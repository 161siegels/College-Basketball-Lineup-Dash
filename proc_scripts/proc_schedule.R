library(bigballR)
library(ncaahoopR)
library(hoopR)
library(dplyr)
library(RMySQL)
library(dbx)
library(readr)
library(doParallel)
library(stringi)
library(tidyr)



season = "2021-22"
connection <- dbConnect(MySQL(), user = 'root', password = 'tarheels2020', host = 'localhost', dbname = 'CBB')
team_ids<-dbGetQuery(connection,paste0("SELECT DISTINCT NCAATeamId FROM CBB.Proc_Teams WHERE Season='", season, "';"))
cores=detectCores()
cl <- makeCluster(cores[1]-1) #not to overload your computer
registerDoParallel(cl)

# NCAA Schedule
sched<-foreach(tm_id=team_ids$NCAATeamId, .combine=bind_rows) %dopar% {
  tryCatch({
    tm_sched = bigballR::get_team_schedule(season = season, team.id = tm_id)
  },
  error = function(e){
    print(e)
    print(tm_id)
    tm_sched = data.frame()
  })
  tm_sched
}
stopCluster(cl)

# ESPN Schedule
# team_ids<-dbGetQuery(connection,paste0("SELECT DISTINCT ESPN_TeamName FROM CBB.Proc_Teams WHERE Season='", season, "';"))
# cores=detectCores()
# cl <- makeCluster(cores[1]-1) 
# registerDoParallel(cl)
# espn_sched<-foreach(tm_nm=team_ids$ESPN_TeamName, .combine=bind_rows) %dopar% {
#   tryCatch({
#     tm_sched <- ncaahoopR::get_schedule(team=tm_nm, season = season)
#     tm_sched$team <- tm_nm
#     tm_sched
#   },
#   error = function(e){
#     tm_sched = data.frame()
#     tm_sched
#   })
# }
# stopCluster(cl)

### Write NCAA import table

teams<-dbGetQuery(connection,paste0("SELECT * FROM CBB.Proc_Teams WHERE Season='", season, "';"))
ncaa_sched <- sched %>%
  rename(GameId=Game_ID, HomeTeamName=Home, AwayTeamName=Away, HomeTeamScore=Home_Score, AwayTeamScore=Away_Score) %>%
  inner_join(teams %>% select(Season, HomeTeamName=TeamName, NCAAHomeTeamId=NCAATeamId)) %>%
  inner_join(teams %>% select(AwayTeamName=TeamName, NCAAAwayTeamId=NCAATeamId)) %>%
  mutate(Date=as.Date(Date, "%m/%d/%Y"),
         GameId=as.integer(GameId)) %>%
  distinct(GameId, .keep_all=TRUE) %>%
  filter(!is.na(GameId)) %>%
  select(GameId, Season, Date, isNeutral, NCAAHomeTeamId, HomeTeamName, NCAAAwayTeamId, AwayTeamName, HomeTeamScore,AwayTeamScore)
dbxUpsert(connection, "Import_NCAA_Schedule", ncaa_sched, where_cols = c("GameId"))

# ESPN Schedule
espn_sched <-load_mbb_team_box(seasons=as.integer(substring(season,1,4))+1) %>%
  filter(home_away=="AWAY") %>%
  rename(ESPN_GameId=game_id, Season=season, ESPN_HomeTeamId=team_id, ESPN_HomeTeamAbbreviation=team_abbreviation, 
         ESPN_AwayTeamId=opponent_id, ESPN_AwayTeamAbbreviation=opponent_abbrev) %>%
  mutate(Date=as.Date(game_date),
         DateMinusOne=as.Date(game_date)-1,
         ESPN_GameId=as.integer(ESPN_GameId),
         ESPN_HomeTeamId=as.integer(ESPN_HomeTeamId),
         ESPN_AwayTeamId=as.integer(ESPN_AwayTeamId),)%>%
  select(ESPN_GameId,Date, DateMinusOne, ESPN_HomeTeamId,  ESPN_HomeTeamAbbreviation, ESPN_AwayTeamId, ESPN_AwayTeamAbbreviation )


all_sched <- ncaa_sched %>% 
  inner_join(teams %>% select(HomeTeamId=TeamId, ESPN_HomeTeamId=ESPN_TeamId, NCAAHomeTeamId=NCAATeamId)) %>% 
  inner_join(teams %>% select(AwayTeamId=TeamId, ESPN_AwayTeamId=ESPN_TeamId, NCAAAwayTeamId=NCAATeamId)) %>%
  left_join(espn_sched %>% select(-DateMinusOne)) %>%
  filter(!is.na(ESPN_GameId))

all_sched_gd <- ncaa_sched %>% 
  inner_join(teams %>% select(HomeTeamId=TeamId, ESPN_HomeTeamId=ESPN_TeamId, NCAAHomeTeamId=NCAATeamId)) %>% 
  inner_join(teams %>% select(AwayTeamId=TeamId, ESPN_AwayTeamId=ESPN_TeamId, NCAAAwayTeamId=NCAATeamId)) %>%
  left_join(espn_sched %>% select(-Date) %>% rename(Date=DateMinusOne)) %>%
  filter(!is.na(ESPN_GameId))
# flip teams for neutral games
all_sched_neut <- ncaa_sched %>% 
  filter(isNeutral==1, !GameId %in% c(all_sched$GameId, all_sched_gd$GameId)) %>%
  inner_join(teams %>% select(HomeTeamId=TeamId, ESPN_HomeTeamId=ESPN_TeamId, NCAAHomeTeamId=NCAATeamId)) %>% 
  inner_join(teams %>% select(AwayTeamId=TeamId, ESPN_AwayTeamId=ESPN_TeamId, NCAAAwayTeamId=NCAATeamId)) %>%
  left_join(espn_sched %>% select(-DateMinusOne)%>% 
              mutate(ESPN_HomeTeamIdTemp=ESPN_AwayTeamId,
                     ESPN_AwayTeamId=ESPN_HomeTeamId,
                     ESPN_HomeTeamId=ESPN_HomeTeamIdTemp,
                     ESPN_HomeTeamAbbreviationTemp=ESPN_AwayTeamAbbreviation,
                     ESPN_AwayTeamAbbreviation=ESPN_HomeTeamAbbreviation,
                     ESPN_HomeTeamAbbreviation=ESPN_HomeTeamAbbreviationTemp)) %>%
  filter(!is.na(ESPN_GameId)) %>%
  select(-ESPN_HomeTeamIdTemp, -ESPN_HomeTeamAbbreviationTemp)

all_sched_neut_gd <- ncaa_sched %>% 
  filter(isNeutral==1, !GameId %in% c(all_sched$GameId, all_sched_gd$GameId)) %>%
  inner_join(teams %>% select(HomeTeamId=TeamId, ESPN_HomeTeamId=ESPN_TeamId, NCAAHomeTeamId=NCAATeamId)) %>% 
  inner_join(teams %>% select(AwayTeamId=TeamId, ESPN_AwayTeamId=ESPN_TeamId, NCAAAwayTeamId=NCAATeamId)) %>%
  left_join(espn_sched %>% select(-Date) %>% rename(Date=DateMinusOne) %>%
              mutate(ESPN_HomeTeamIdTemp=ESPN_AwayTeamId,
                     ESPN_AwayTeamId=ESPN_HomeTeamId,
                     ESPN_HomeTeamId=ESPN_HomeTeamIdTemp,
                     ESPN_HomeTeamAbbreviationTemp=ESPN_AwayTeamAbbreviation,
                     ESPN_HomeTeamAbbreviation=ESPN_AwayTeamAbbreviation,
                     ESPN_AwayTeamAbbreviation=ESPN_HomeTeamAbbreviation,
                     ESPN_HomeTeamAbbreviation=ESPN_HomeTeamAbbreviationTemp)) %>%
  filter(!is.na(ESPN_GameId)) %>%
  select(-ESPN_HomeTeamIdTemp, -ESPN_HomeTeamAbbreviationTemp)

dbxUpsert(connection, "Proc_Schedule", bind_rows(all_sched, all_sched_gd, all_sched_neut, all_sched_neut_gd), where_cols = c("GameId"))
