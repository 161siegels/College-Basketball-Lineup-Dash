library(bigballR)
library(ncaahoopR)
library(hoopR)
library(dplyr)
library("RMySQL")
library(dbx)
library(readr)
library(doParallel)
library(stringi)


# Get ncaa pbp for stanford
season = "2021-22"
team = "Stanford"
sched = get_team_schedule(season = season, team.name = team)
pbp <- get_play_by_play(game_ids = gamesched$Game_ID)

# Get shot numbers
pbp <- pbp %>%
  mutate(
    FGA = as.integer(Shot_Value>1),
    FTA = as.integer(Shot_Value==1),
    TotalScore = Home_Score + Away_Score,
    Date=as.Date(Date, "%m/%d/%Y")
  ) %>%
  group_by(ID) %>%
  arrange(Game_Seconds) %>%
  mutate(
    ShotNumber = cumsum(coalesce(FGA, 0)) + FGA*0,
    PlayNumber = cumsum(!is.na(ID))
  )

# Get espn pbp
espn_sched <- get_schedule(team=team, season = "2021-22")
espn_pbp <- get_pbp(team=team, season = season, extra_parse = T)


mbb_pbp <- mbb_pbp %>%
  inner_join(espn_sched %>% select(game_id, date)) %>%
  mutate(
    ESPN_FGA = ifelse((score_value>=2) | ((score_value==1) & (is.na(type_text))), 1, NA),
    ESPN_FTA = ifelse((score_value==1) & (!is.na(type_text)), 1, NA),
    ESPN_TotalScore = home_score+away_score,
    Date = as.Date(game_date),
    ESPN_Game_Seconds = (2400+(as.integer(half)-2)*300) - 60*as.integer(clock_minutes) - as.integer(clock_seconds)
  ) %>%
  group_by(game_id) %>%
  arrange(ESPN_Game_Seconds, -ESPN_TotalScore, -as.integer(sequence_number), desc=TRUE) %>%
  mutate(
    ESPN_ShotNumber = cumsum(coalesce(ESPN_FGA, 0)) + ESPN_FGA*0,
    PlayNumber = cumsum(!is.na(game_id))
  )

shot_info <- mbb_pbp %>%
  rename(
    ESPN_GameId = game_id,
    ESPN_Home_TeamName=home_team_name,
    ESPN_Home_TeamId=home_team_id,
    ESPN_Away_TeamName=away_team_name,
    ESPN_Away_TeamId=away_team_id,
    ESPN_Home_Score=home_score,
    ESPN_Away_Score=away_score,
    ESPN_Description=text,
    ESPN_Player1Id=participants_0_athlete_id,
    ESPN_Player2Id=participants_1_athlete_id,
    ESPN_Shot_X = coordinate_x,
    ESPN_Shot_Y = coordinate_y,
  ) %>%
  # only need shots
  filter(!is.na(ESPN_ShotNumber)) %>%
  select(
    Date, ESPN_GameId, ESPN_Home_TeamName, ESPN_Home_TeamId, ESPN_Away_TeamName, ESPN_Away_TeamId,
    ESPN_Home_Score, ESPN_Away_Score,
    ESPN_Description, ESPN_Player1Id, ESPN_Player2Id, ESPN_Shot_X, ESPN_Shot_Y, ESPN_ShotNumber
  )


### Create Team Map
teams <- bigballR::teamids %>% 
  rename(TeamName=Team, NCAATeamId=ID) %>%
  group_by(TeamName) %>% 
  mutate(
    TeamId = cur_group_id()
  )

espn_teams <- ncaahoopR::ids %>%
  rename(ESPN_TeamName=team, ESPN_TeamId=id) %>%
  as.data.frame() %>%
  mutate(
    AutoMapped = (ESPN_TeamName %in% teams$TeamName)
  )

team_map <- read_csv("team_map.csv")

new_teams_to_map <- espn_teams %>%
  filter(!AutoMapped) %>%
  filter(!(ESPN_TeamName %in% team_map$ESPN_TeamName))

print(paste(nrow(new_teams_to_map), "new teams to map!"))
if(nrow(new_teams_to_map)>0){
  # Write csvs
  team_map %>%
    bind_rows(new_teams_to_map) %>%
    write.csv("team_map.csv", row.names = FALSE)
  teams %>% write.csv("all_teams.csv", row.names = FALSE)
}


# map teams
team_map <- read_csv("team_map.csv")
espn_teams <- espn_teams %>% 
  filter(AutoMapped) %>%
  inner_join(
    (teams %>% group_by(TeamId) %>% summarise(TeamName=TeamName[1])), 
    by=c("ESPN_TeamName"="TeamName")
  ) %>%
  bind_rows(team_map) %>%
  select(-AutoMapped)


teams <- left_join(teams, espn_teams) %>%
  as.data.frame()

sum(is.na(teams$ESPN_TeamName))

saveRDS(teams, file="teams.RDS")
connection <- dbConnect(MySQL(), user = 'root', password = 'tarheels2020', host = 'localhost', dbname = 'CBB')
dbxUpsert(connection, "Proc_Teams", teams %>% select(-link), where_cols = c("NCAATeamId"))

###

### Players
team_szn <- teams
players <- data.frame()
cores=detectCores()
cl <- makeCluster(cores[1]-1) #not to overload your computer
registerDoParallel(cl)

players<-foreach(tm_id=team_szn$NCAATeamId, .combine=bind_rows) %dopar% {
  tryCatch({  print(tm_id)
    roster <- bigballR::get_team_roster(team.id=tm_id)
    roster$NCAATeamId <- tm_id
    roster$Jersey = as.integer(roster$Jersey)
    roster},
    error = function(e){
      Sys.sleep(0)
      roster <- bigballR::get_team_roster(team.id=tm_id)
      roster$NCAATeamId <- tm_id
      roster$Jersey = as.integer(roster$Jersey)
      roster
    })
}
# dedup
players <- players %>%
  distinct(Player, NCAATeamId, Jersey, .keep_all=TRUE)

espn_players <- hoopR::load_mbb_player_box(seasons=seq(2003, most_recent_mbb_season()-1)) %>% 
  group_by(team_id, athlete_id, athlete_display_name, athlete_jersey, season) %>% 
  summarise(games=n()) %>% 
  as.data.frame() %>%
  mutate(Season = paste0(season-1,"-",season%%100))
stopCluster(cl)
cores=detectCores()
cl <- makeCluster(cores[1]-1) #not to overload your computer
registerDoParallel(cl)
espn_players_2<-foreach(tm_nm=unique(team_szn$ESPN_TeamName), .combine=bind_rows) %dopar% {
  print(tm_nm)
  if(!is.na(tm_nm)){
    tryCatch(
      {
        roster <- ncaahoopR::get_roster(team=tm_nm, season="2021-22")
        roster$ESPN_TeamName <- tm_nm
        roster$ESPN_PlayerId <- gsub(".png", "", gsub("^.*/", "", roster$player_image))
        roster$Season = paste0(most_recent_mbb_season()-1, "-", most_recent_mbb_season()%%100)
        roster<-as.data.frame(roster)
      },
      error = function(e){
        roster<-data.frame()
      }
    )
  }else{
    roster<-data.frame()
  }
  roster
}

espn_players <- espn_players %>%
  rename(name=athlete_display_name, ESPN_PlayerId=athlete_id, ESPN_TeamId=team_id, number=athlete_jersey) %>%
  mutate(ESPN_TeamId = as.integer(ESPN_TeamId),
         number = as.integer(number)) %>%
  bind_rows(espn_players_2 %>% inner_join(teams)) %>%
  mutate(
    ESPN_PlayerId = as.integer(ESPN_PlayerId)
  ) %>%
  rename(Jersey=number) %>%
  distinct(ESPN_TeamId, Season, ESPN_PlayerId, .keep_all=TRUE)

espn_players$MapName <- stri_replace_all_regex(tolower(espn_players$name),
                                                 pattern=c(" jr.$", " sr.$", " ii.$", " iii.$", " iv.$", "\\'", "\\."),
                                                 replacement='',
                                                 vectorize=FALSE)
players$MapName <- stri_replace_all_regex(tolower(players$CleanName),
                                            pattern=c(" jr.$", " sr.$", " ii.$", " iii.$", " iv.$", "\\'", "\\."),
                                            replacement='',
                                            vectorize=FALSE)


# Map by jersey then by name
espn_with_jersey <- espn_players %>% 
  group_by(Jersey, Season, ESPN_TeamId) %>%
  mutate(count = n()) %>%
  filter(count==1) %>%
  ungroup()

espn_with_name <- espn_players %>% 
  group_by(MapName, Season, ESPN_TeamId) %>%
  mutate(count = n()) %>%
  filter(count==1) %>%
  ungroup()

players_name <- players %>% 
  left_join(teams %>% select(TeamId, TeamName, NCAATeamId, ESPN_TeamId,ESPN_TeamName, Season)) %>%
  left_join(espn_with_name %>%
              select(ESPN_PlayerId, MapName, ESPN_TeamId, Season) ) %>%
  mutate(AutoMapped = !is.na(ESPN_PlayerId))

players_jersey <- players_name %>% 
  filter(!AutoMapped) %>%
  select(-ESPN_PlayerId) %>%
  left_join(espn_with_jersey %>%
              select(ESPN_PlayerId, Jersey, ESPN_TeamId, Season) ) %>%
  mutate(AutoMapped = !is.na(ESPN_PlayerId))

# Write players as Import NCAA Players
# Write ESPN players as Import ESPN Players
# bind rows of players_name and players_jersey fro Proc Players
connection <- dbConnect(MySQL(), user = 'root', password = 'tarheels2020', host = 'localhost', dbname = 'CBB')
ncaa_players <- players %>%
  inner_join(teams %>% select(NCAATeamId, Season)) %>%
  mutate(Jersey = ifelse(is.na(Jersey), -1, Jersey)) %>%
  select(NCAAPlayerName=Player, NCAATeamId, Season, Jersey, Pos, Yr, HtInches, NCAAPlayerCleanName=CleanName, MapName)
dbxUpsert(connection, "Import_NCAA_Players", ncaa_players, where_cols = c("NCAAPlayerName", "NCAATeamId", "Jersey"))

espn_players_write <- espn_players %>%
  inner_join(teams %>% ungroup() %>% select(NCAATeamId, ESPN_TeamId, Season)) %>%
  select(ESPN_PlayerId, ESPN_TeamId, NCAATeamId, Season, ESPN_Jersey = Jersey, ESPN_MapName=MapName)
dbxUpsert(connection, "Import_NCAA_Players", ncaa_players, where_cols = c("NCAAPlayerName", "NCAATeamId", "Jersey"))

player_map <- read_csv("player_map.csv")
new_players_to_map <- filter(players, !AutoMapped, !ESPN_PlayerId %in% player_map$PlayerId)

if(nrow(new_players_to_map)>0){
  # Write csvs
  player_map %>%
    bind_rows(new_players_to_map) %>%
    write.csv("player_map.csv", row.names = FALSE)
  espn_players %>% write.csv("all_espn_players.csv", row.names = FALSE)
}


# map teams
player_map <- read_csv("player_map.csv")
players <- players %>% 
  filter(AutoMapped) %>%
  bind_rows(player_map) %>%
  filter(!is.na(ESPN_PlayerId))%>%
  select(-AutoMapped)





###

shots <- pbp %>% 
  inner_join(shot_info, by.x = c(Date, ))







shot_locs <- get_shot_locs(espn_sched$game_id)
opp_shot_chart(espn_sched$game_id, team, heatmap = T)
team_shot_chart(espn_sched$game_id, team, heatmap = T)

get_team_roster(team.id = 1)


roster_proc <- function (team, season = "2021-22") 
{
  if (is.na(team)) {
    stop("team is missing with no default")
  }
  if (!"ncaahoopR" %in% .packages()) {
    ids <- create_ids_df()
  }
  if (!team %in% ids$team) {
    stop("Invalid team. Please consult the ids data frame for a list of valid teams, using data(ids).")
  }
  if (season == "2021-22") {
    base_url <- "https://www.espn.com/mens-college-basketball/team/roster/_/id/"
    url <- paste(base_url, ids$id[ids$team == team], "/", 
                 ids$link[ids$team == team], sep = "")
    content <- RCurl::getURL(url)
    tmp <- try(XML::readHTMLTable(content))
    if (class(tmp) == "try-error") {
      warning("Unable to get roster. ESPN is updating CBB files. Check back again soon")
      return(NULL)
    }
    tmp <- as.data.frame(tmp[[1]])
    names(tmp) <- c("number", "name", "position", "height", 
                    "weight", "class", "hometown")
    player_ids <- XML::getHTMLLinks(content) %>% stringr::str_subset(., 
                                                                     "mens-college-basketball/player/_/id") %>% unique() %>% 
      stringr::str_extract(., "[0-9]{7}")
    for (i in 1:ncol(tmp)) {
      tmp[, i] <- as.character(tmp[, i])
    }
    tmp$number <- as.numeric(gsub("[^0-9]", "", tmp$name))
    tmp$name <- gsub("[0-9]*", "", tmp$name)
    tmp$player_image <- paste0("https://a.espncdn.com/combiner/i?img=/i/headshots/mens-college-basketball/players/full/", 
                               player_ids, ".png")
    tmp <- dplyr::arrange(tmp, number)
    return(tmp)
  }
  else {
    roster <- suppressWarnings(try(readr::read_csv(paste0("https://raw.githubusercontent.com/lbenz730/ncaahoopR_data/master/", 
                                                          season, "/rosters/", gsub(" ", "_", team), "_roster.csv"), 
                                                   show_col_types = F)))
    if (any(class(roster) == "try-error")) {
      warning("No Roster Available")
      return(NULL)
    }
    return(roster)
  }
}

