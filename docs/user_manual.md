In order to use a BoogieStats instance as your score aggregator you will have to follow the steps below.
If you already have GrooveStats integration up and running in **ITGmania** (I don't support GrooveStats Launcher
method anymore), you can skip to [Join and Enable BoogieStats section](#join-and-enable-boogiestats).

## Join and Enable GrooveStats

1. Download and install ITGmania from the [official website](https://www.itgmania.com/). 
  Optionally, migrate your profile form SM5 (if you have one) using [the following guide](https://github.com/itgmania/itgmania/blob/release/Docs/Userdocs/sm5_migration.md). 

2. Start the game, create a profile (if you haven't migrated a profile) and set it to a desired player slot.

3. `Sign Up` and generate an `API Key` on [GrooveStats](https://groovestats.com/).

4. Set `Enable GrooveStats` to `Yes` in the `GrooveStats Options` inside the `Game Options` submenu of `Options`.

5. Configure GrooveStats in your profile by creating a `GrooveStats.ini` file inside your profile directory.
  You will find your `Save` directory inside `%appdata%` if you picked a normal installer version of ITGmania,
  or directly inside the game directory in case of "portable" installation.
  For example: `Save/LocalProfiles/00000000/GrooveStats.ini` should have the following contents:
```
[GrooveStats]
ApiKey=your API key from groovestats.com
IsPadPlayer=1
```

## Join and Enable BoogieStats

1. Modify `Simply Love` theme to redirect request from `api.groovestats.com` to your BoogieStats URL.
  Find and modify `ITGMANIA_PATH/Themes/Simply Love/Scripts/SL-Helpers-GrooveStats.lua` -- change line 44 from:
```
local url_prefix = "https://api.groovestats.com/"
```
  to:
```
local url_prefix = "https://your.boogiestats.url/"
```

2. Allow ITGmania to make network requests to your BoogieStats URL.
 Locate your `Save` directory the same way as in the previous step.
  Find and modify `Save/Preferences.ini` -- change line 95 from:
```
HttpAllowHosts=*.groovestats.com
```
to:
```
HttpAllowHosts=*.groovestats.com,your.boogiestats.url
```
  It's important to still allow the usual GrooveStats requests in order to allow downloads of unlockable songs in the
  future contests held by GrooveStats.

3. Play and pass any song to automatically create an account on BoogieStats.

4. Edit your profile on BoogieStats.
  Use your GrooveStats API key to log in (you can try to paste the whole key, it will be automatically cut to the limit 
  inside the form). You can set as many Rivals as you want, only the top 3 will be used when more of them completed
  a song that you request a leaderboard for in game.

5. Enjoy!

## Q&A
- **Q:** Will the scores be saved to GrooveStats when I use BoogieStats?  
  **A:** Yes! BoogieStats acts as a proxy for GrooveStats.
     It records all received scores and also passes them to GrooveStats.
     When you retrieve scores in the game, the ones from GrooveStats will take precedence so the behavior for "ranked" songs should remain the same.
- **Q:** Is it safe?  
  **A:** It's probably as safe as using a USB Profile on a public PC in an arcade or during a convention. I don't store your GrooveStats API key in a clear form, and the whole key is used only during forwarding scores to GrooveStats. You can inspect the code [on my GitHub](https://github.com/florczakraf/boogie-stats) or host the app for yourself if you don't plan to use the comparison & leaderboards features.
- **Q:** What if I play a ranked song? What scores will I see?  
  **A:** You will receive an official leaderboard from GroovStats in your game.
     However, in the UI of BoogieStats, only the local scores will be displayed for a given song, with an information that it's a ranked song and the leaderboard might be incomplete.
- **Q:** What if I play a song that's not in your database?  
  **A:** BoogieStats will automatically accept and track it. It will look like any other ranked song in your game. In the UI, the song will display a song hash instead of a title until it's information is added to the [public database](https://github.com/florczakraf/stepmania-chart-db). Please send me a list of packs that are missing when you encounter this issue.
- **Q:** Will you support `Stats.xml` or [simply.training](https://simply.training) jsons?  
  **A:**  Not in the current form. They don't use the unique song identifiers and I'm not going to try and match songs by their paths, which has already been proven by GrooveStats to be a tedious, troublesome and ambiguous.
- **Q:** Do events held by GrooveStats and the related leaderboards work with BoogieStats?  
  **A:** ITL and SRPG as well as their custom leaderboards are supported. As for the other events, it's probably a matter of a little time if they introduce a custom API. Additionally, the event songs that are "unranked" in GrooveStats will still be recorded in BoogieStats.
- **Q:** What if a song becomes "ranked" on GrooveStats after it's been recorded in BoogieStats?  
  **A:** That hasn't been a case so far but if it's going to happen, I will probably introduce a way to export old highscores to GrooveStats. I won't be able to do it automatically because I don't store your API key, so it will require you to provide a full key in the UI. I could also generate a list of QR codes / links for you to export them manually.
- **Q:** Will it work in a public arcade with a USB Profile?  
  **A:** It could if `Simply Love` and `Preferences.ini` were modified on the machine as described in [Join and Enable BoogieStats section](#join-and-enable-boogiestats). However, I don't recommend it for public machines because their users might not be aware that their GrooveStats API key would be exposed to a 3rd-party proxy.