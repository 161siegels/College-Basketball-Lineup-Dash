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
library(arrow)

season = "2021-22"
connection <- dbConnect(MySQL(), user = 'root', password = 'tarheels2020', host = 'localhost', dbname = 'CBB')
players<-dbGetQuery(connection,paste0("SELECT * FROM CBB.Proc_Players WHERE Season='", season, "';"))
games<-dbGetQuery(connection,paste0("SELECT * FROM CBB.Proc_Schedule WHERE Season='", season, "';"))
teams<-dbGetQuery(connection,paste0("SELECT * FROM CBB.Proc_Teams WHERE Season='", season, "';"))

raw_pbp <- get_play_by_play(game_ids =unique(games$GameId))
saveRDS(raw_pbp, file=paste0("pbp", season,".RDS"))

# Get shot numbers
pbp <- raw_pbp %>%
  mutate(
    FGA = as.integer(Shot_Value>1),
    FTA = as.integer(Shot_Value==1),
    FGA = ifelse(FTA==1, NA, FGA),
    TotalScore = Home_Score + Away_Score,
    Date=as.Date(Date, "%m/%d/%Y"),
    GameId=as.integer(ID)
  ) %>%
  group_by(ID) %>%
  arrange(TotalScore, Game_Seconds) %>%
  mutate(
    ShotNumber = cumsum(coalesce(FGA, 0)) + FGA*0,
    PlayNumber = cumsum(!is.na(ID)),
    MaxShotNumber = max(ShotNumber,na.rm=TRUE)
  ) %>%
  ungroup() %>%
  filter(is.finite(MaxShotNumber))


mbb_pbp <- load_mbb_pbp(seasons=as.integer(substring(season,1,4))+1) 
mbb_pbp <- mbb_pbp %>%
  inner_join(games %>% select(GameId, Date, game_id=ESPN_GameId)) %>%
  mutate(
    ESPN_FGA = ifelse((score_value>=2) | ((score_value==1) & (is.na(type_text))), 1, NA),
    ESPN_FTA = ifelse((score_value==1) & (!is.na(type_text)), 1, NA),
    ESPN_TotalScore = home_score+away_score,
    Date = as.Date(Date),
    ESPN_Game_Seconds = ifelse(qtr<2, 1200, ifelse(qtr<3, 2400, 2400+300*(qtr-2))) - 60*as.integer(clock_minutes) - as.integer(clock_seconds)
  ) %>%
  group_by(game_id) %>%
  arrange(ESPN_TotalScore, ESPN_Game_Seconds, -as.integer(sequence_number), desc=TRUE) %>%
  mutate(
    ESPN_ShotNumber = cumsum(coalesce(ESPN_FGA, 0)) + ESPN_FGA*0,
    PlayNumber = cumsum(!is.na(game_id)),
    MaxESPN_ShotNumber = max(ESPN_ShotNumber, na.rm=TRUE)
  ) %>%
  ungroup()

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
    GameId, ESPN_GameId, ESPN_Home_TeamName, ESPN_Home_TeamId, ESPN_Away_TeamName, ESPN_Away_TeamId,
    ESPN_Home_Score, ESPN_Away_Score, ESPN_Game_Seconds,MaxESPN_ShotNumber,
    ESPN_Description, ESPN_Player1Id, ESPN_Player2Id, ESPN_Shot_X, ESPN_Shot_Y, ESPN_ShotNumber
  )
###

pbp <- pbp %>%
  inner_join(teams %>% select(Home=TeamName, HomeTeamId=TeamId, NCAAHomeTeamId=NCAATeamId)) %>%
  inner_join(teams %>% select(Away=TeamName, AwayTeamId=TeamId, NCAAAwayTeamId=NCAATeamId)) %>%
  left_join(teams %>% select(Event_Team=TeamName, EventTeamId=TeamId, NCAAEventTeamId=NCAATeamId)) %>%
  left_join(players %>% select(Player_1=NCAAPlayerName, Player1Id=ESPN_PlayerId, NCAAEventTeamId=NCAATeamId)) %>%
  left_join(players %>% select(Player_2=NCAAPlayerName, Player2Id=ESPN_PlayerId, NCAAEventTeamId=NCAATeamId))
  
for(col in c(paste0("Home.", 1:5), paste0("Away.", 1:5))){
  hm_away_col = ifelse(grepl("Home", col), "NCAAHomeTeamId", "NCAAAwayTeamId")
  new_col= paste0(gsub("\\.","Player",col), "Id")
  pbp <- pbp %>%
    left_join(players %>% select(NCAAPlayerName, ESPN_PlayerId, NCAATeamId) %>%
                setNames(c(paste(col),paste(new_col), paste(hm_away_col))) )
}
# Write PBP
# Write Shots

proc_pbp <- pbp %>% 
  left_join(shot_info, by= c("GameId"="GameId", "MaxShotNumber"="MaxESPN_ShotNumber",
                              "ShotNumber"="ESPN_ShotNumber")) %>% 
  group_by(GameId) %>% 
  arrange(PlayNumber) %>% 
  mutate(
    # only marginal points when on offense
    HomeMarginalPoints = Home_Score -lag(Home_Score, default=0),
    AwayMarginalPoints = Away_Score -lag(Away_Score, default=0),
    HomeMarginalPoints=ifelse(is.na(HomeMarginalPoints),0,HomeMarginalPoints),
    AwayMarginalPoints=ifelse(is.na(AwayMarginalPoints),0,AwayMarginalPoints)
  ) %>%
  ungroup() %>%
  mutate(
    Event_Type = ifelse(Event_Type=="Unk", "Dunk", Event_Type),
    NCAANonEventTeamId= ifelse(NCAAEventTeamId==NCAAHomeTeamId, NCAAAwayTeamId, NCAAHomeTeamId),
    NCAAOffTeamId = ifelse(Event_Type %in% c("won Jumpball", "Three Point Jumper", "Two Point Jumper", "Hook",
                                             "Turnover", "Offensive Rebound", "Layup", "Draw Foul",
                                             "Free Throw", "Dunk", "null Turnover", "Tip In" ),
                           NCAAEventTeamId, NCAANonEventTeamId),
    NCAADefTeamId = ifelse(Event_Type %in% c("Defensive Rebound", "Steal", "Commits Foul", "Blocked Shot",
                                             "lost Jumpball"), NCAAEventTeamId, NCAANonEventTeamId),
    NCAAOffTeamId = ifelse(Event_Type %in% c("Media Timeout", "Team Timeout", "Second Timeout", "ERROR CHECK THE EVENT",
                                             "Timeout", "Leaves Game", "Enters Game", "ERROR CHECK THE EVENT", "media Timeout",
                                             "Deadball Rebound", "held Jumpball"),
                           NA, NCAAOffTeamId),
    NCAADefTeamId = ifelse(Event_Type %in% c("Media Timeout", "Team Timeout", "Second Timeout", "ERROR CHECK THE EVENT",
                                             "Timeout", "Leaves Game", "Enters Game", "ERROR CHECK THE EVENT", "media Timeout",
                                             "Deadball Rebound", "held Jumpball"),
                           NA, NCAADefTeamId),
    NCAAOffTeamId = case_when( is.na(NCAAOffTeamId) & is.na(NCAADefTeamId) & (HomeMarginalPoints>0)~NCAAHomeTeamId,
                               is.na(NCAAOffTeamId) & is.na(NCAADefTeamId) & (AwayMarginalPoints>0)~NCAAAwayTeamId,
                               TRUE~NCAAOffTeamId),
    NCAADefTeamId = ifelse(NCAAOffTeamId==NCAAHomeTeamId, NCAAAwayTeamId, NCAAHomeTeamId)
  ) %>%
  group_by(GameId) %>% 
  arrange(PlayNumber) %>% 
  fill(NCAAOffTeamId, NCAADefTeamId, .direction = "down") %>%
  ungroup() %>%
  group_by(GameId, NCAAOffTeamId) %>% 
  arrange(PlayNumber) %>% 
  mutate(
        # only marginal points when on offense
         HomeMarginalPoints = ifelse(NCAAOffTeamId==NCAAHomeTeamId,
                                     Home_Score -lag(Home_Score, default=0), 0),
         AwayMarginalPoints = ifelse(NCAAOffTeamId==NCAAAwayTeamId,
                                     Away_Score -lag(Away_Score, default=0), 0),
         HomeMarginalPoints=ifelse(is.na(HomeMarginalPoints),0,HomeMarginalPoints),
         AwayMarginalPoints=ifelse(is.na(AwayMarginalPoints),0,AwayMarginalPoints)
         ) %>%
  select(
  GameId, Home, Away, HomeTeamId, AwayTeamId, NCAAHomeTeamId, NCAAAwayTeamId,
  GameSeconds=Game_Seconds, HomeScore=Home_Score, AwayScore=Away_Score, PossNum=Poss_Num, PlayNumber, ShotNumber,
  EventDescription=Event_Description, EventType=Event_Type, EventResult=Event_Result,HomeMarginalPoints, AwayMarginalPoints,
  Event_Length=Event_Length, Poss_Length=Poss_Length, Transition=isTransition, ShotValue=Shot_Value, 
  GarbageTime=isGarbageTime, 
  FGA, FTA, NCAAEventTeamId, NCAANonEventTeamId, NCAAOffTeamId, NCAADefTeamId,
  Player1Name=Player_1, Player2Name=Player_2,
  HomePlayer1Name=Home.1, HomePlayer2Name=Home.2, HomePlayer3Name=Home.3, HomePlayer4Name=Home.4, HomePlayer5Name=Home.5,
  AwayPlayer1Name=Away.1, AwayPlayer2Name=Away.2, AwayPlayer3Name=Away.3, AwayPlayer4Name=Away.4, AwayPlayer5Name=Away.5,
  Player1Id, Player2Id, 
  HomePlayer1Id, HomePlayer2Id, HomePlayer3Id, HomePlayer4Id, HomePlayer5Id, 
  AwayPlayer1Id, AwayPlayer2Id, AwayPlayer3Id, AwayPlayer4Id, AwayPlayer5Id, 
  ESPN_Player1Id, ESPN_Player2Id, ESPN_Shot_X, ESPN_Shot_Y, ESPN_Description
) %>%
  inner_join(games %>% select(GameId, Season, Date) %>% mutate(Date=as.Date(Date)))

dbxUpsert(connection, "Proc_PBP", proc_pbp, where_cols = c("GameId", "PlayNumber"),
          batch_size=5000)

# TODO: MANUALLY FIX BAD PBP
bad_games =proc_pbp %>% 
  group_by(GameId) %>% 
  summarise(hscore = sum(HomeMarginalPoints), maxhscore=max(HomeScore),
            ascore = sum(AwayMarginalPoints), maxascore=max(AwayScore)) %>%
  filter((hscore!=maxhscore) | (ascore!=maxascore)) %>%
  pull(GameId)
print(bad_games)

write_dataset(
  proc_pbp,
  paste0("pbp", season,".parquet"),
  format = c("parquet"),
  partitioning = "Season"
)

