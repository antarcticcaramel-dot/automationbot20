// src/events/ready.js
const { REST, Routes, ActivityType } = require('discord.js');
const fs = require('fs');
const path = require('path');

module.exports = {
  name: 'ready',
  once: true,
  async execute(client) {
    console.log(`\n🚀 Logged in as ${client.user.tag}`);

    // Set bot status
    client.user.setPresence({
      activities: [{ name: '✨ Managing your server', type: ActivityType.Watching }],
      status: 'online'
    });

    // Register slash commands
    const commands = [];
    const commandsPath = path.join(__dirname, '../commands');
    fs.readdirSync(commandsPath).filter(f => f.endsWith('.js')).forEach(file => {
      const cmd = require(path.join(commandsPath, file));
      if (cmd.data) commands.push(cmd.data.toJSON());
    });

    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
      await rest.put(
        Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
        { body: commands }
      );
      console.log(`✅ Registered ${commands.length} slash commands`);
    } catch (err) {
      console.error('❌ Failed to register commands:', err);
    }

    console.log('✅ Bot fully ready!\n');
  }
};
