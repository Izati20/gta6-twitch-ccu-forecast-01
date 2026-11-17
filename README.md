# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Izati20/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Izati20/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An ensemble day-shape forecaster for GTA VI's launch-day Twitch viewers: it anchors each past big launch's release-day curve at its first hour, blends the log-ratio shapes of the launches most similar to this one (rolling-midnight unlocks weighted up), and reads its quantile spread from the ensemble's own dispersion. On the four practice launches it scores a mean log pinball loss of 0.162 against the house baseline's 0.387.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=izaati-izati) by @izaati-izati · [Bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) · [Leaderboard](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard)</sub>
