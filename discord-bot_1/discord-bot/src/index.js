// src/index.js
require('dotenv').config();
const { Client, GatewayIntentBits, Partials, Collection } = require('discord.js');
const fs = require('fs');
const path = require('path');
const express = require('express');

// ── Keep-alive server for Render ─────────────────────────────────────────────
const app = express();
app.get('/', (_, res) => res.send('Bot is running ✅'));
app.listen(process.env.PORT || 3000, () => console.log('Keep-alive server running'));

// ── Client setup ─────────────────────────────────────────────────────────────
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessageReactions,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildPresences,
  ],
  partials: [Partials.Message, Partials.Channel, Partials.Reaction, Partials.GuildMember]
});

client.commands = new Collection();

// ── Load event handlers ───────────────────────────────────────────────────────
const eventsPath = path.join(__dirname, 'events');
fs.readdirSync(eventsPath).filter(f => f.endsWith('.js')).forEach(file => {
  const event = require(path.join(eventsPath, file));
  if (event.once) {
    client.once(event.name, (...args) => event.execute(...args, client));
  } else {
    client.on(event.name, (...args) => event.execute(...args, client));
  }
  console.log(`✅ Loaded event: ${event.name}`);
});

// ── Load slash commands ───────────────────────────────────────────────────────
const commandsPath = path.join(__dirname, 'commands');
fs.readdirSync(commandsPath).filter(f => f.endsWith('.js')).forEach(file => {
  const cmd = require(path.join(commandsPath, file));
  if (cmd.data && cmd.execute) {
    client.commands.set(cmd.data.name, cmd);
    console.log(`✅ Loaded command: ${cmd.data.name}`);
  }
});

client.login(process.env.DISCORD_TOKEN);
