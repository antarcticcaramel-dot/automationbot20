# 🤖 Discord Server Bot

A full-featured Discord server management bot with auto-setup, art channel reposting, suggestion voting, boost announcements, self-roles, giveaways, moderation, and more.

---

## 📋 Features

| Feature | Description |
|---|---|
| 🔧 `/setup` | Auto-creates all channels, categories, and roles |
| 🎨 Art Channel | Deletes non-images, reposts artwork with like/dislike buttons |
| 💡 Suggestions | Reposts suggestions as embeds with live vote percentage bars |
| 🚀 Boost Announce | Posts a fancy embed when someone boosts the server |
| 🎭 `/selfroles` | Posts a self-role embed with clickable role buttons |
| 🎁 `/giveaway` | Full giveaway system with timed endings and winner picking |
| 📢 `/announce` | Post fancy colored announcement embeds |
| 📜 `/rules` | Post the server rules embed |
| 💎 `/supporter` | Give/remove the Supporter role manually |
| 🛡️ `/mod` | Warn, timeout, kick, ban, unban, purge |
| 👋 Welcome | Auto-welcomes new members with a fancy embed |
| 🔢 Counting | Auto-validates the counting channel |

---

## 🚀 Setup Guide

### 1. Create your Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → give it a name
3. Go to **Bot** tab → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
   - ✅ Presence Intent
5. Copy your **Bot Token** (keep this secret!)

### 2. Get your IDs

- **Client ID**: Applications page → General Information → Application ID
- **Guild ID**: Right-click your server in Discord → Copy Server ID (enable Developer Mode in Discord settings first)

### 3. Invite the bot

Go to: `https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands`

Replace `YOUR_CLIENT_ID` with your actual Client ID. This gives it Administrator permission (needed for channel/role creation).

### 4. Push to GitHub

1. Create a new **private** repository on GitHub
2. Push this folder to it:
```bash
git init
git add .
git commit -m "Initial bot setup"
git remote add origin https://github.com/YOURUSERNAME/YOURREPO.git
git push -u origin main
```

### 5. Deploy to Render

1. Go to https://render.com → sign in
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Set these settings:
   - **Runtime**: Node
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
5. Add **Environment Variables**:
   | Key | Value |
   |---|---|
   | `DISCORD_TOKEN` | Your bot token |
   | `CLIENT_ID` | Your application/client ID |
   | `GUILD_ID` | Your server ID |
6. Click **Deploy**!

### 6. Run `/setup` in your server

Once the bot is online, type `/setup` in any channel. It will:
- Create all roles
- Create all categories
- Create all channels with proper permissions

Then run:
- `/rules` in your rules channel
- `/selfroles` in your self-roles channel

---

## 📁 Project Structure

```
discord-bot/
├── config/
│   └── serverStructure.js   # Edit this to change channels/roles
├── src/
│   ├── index.js             # Entry point
│   ├── commands/
│   │   ├── setup.js
│   │   ├── selfroles.js
│   │   ├── rules.js
│   │   ├── announce.js
│   │   ├── giveaway.js
│   │   ├── supporter.js
│   │   └── mod.js
│   └── events/
│       ├── ready.js
│       ├── messageCreate.js
│       ├── interactionCreate.js
│       ├── guildMemberAdd.js
│       ├── guildMemberRemove.js
│       └── guildMemberUpdate.js
├── .env.example
├── .gitignore
└── package.json
```

---

## ⚙️ Customisation

**Change channel names/layout**: Edit `config/serverStructure.js`

**Change self-role options**: Edit the `selfRoles` array in `src/commands/selfroles.js`

**Change welcome message**: Edit `src/events/guildMemberAdd.js`

---

## ❓ Troubleshooting

- **Commands not showing up**: Make sure `CLIENT_ID` and `GUILD_ID` are correct. Commands register on startup.
- **Bot can't create channels**: Make sure the bot has Administrator permission.
- **Art channel not working**: Make sure the channel name contains "art".
- **Render bot going to sleep**: Render free tier sleeps after 15 min of inactivity. Use [UptimeRobot](https://uptimerobot.com) to ping your Render URL every 5 minutes to keep it awake.
