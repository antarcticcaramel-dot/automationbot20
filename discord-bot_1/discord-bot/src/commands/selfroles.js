// src/commands/selfroles.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const DISCORD_INVITE = 'https://discord.gg/CZ28Gh3wXG';
const ROBLOX_GROUP   = 'https://www.roblox.com/share/g/35116281';

module.exports = {
  data: new SlashCommandBuilder()
    .setName('selfroles')
    .setDescription('📌 Post the self-roles embed in the current channel')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels),

  async execute(interaction) {
    const guild = interaction.guild;

    // Only 2 self-assignable roles
    const selfRoles = [
      { emoji: '🎨', label: 'Artist',    keyword: 'artist',    description: 'Share your art in #art',        color: 0x34D399, style: ButtonStyle.Success  },
      { emoji: '💡', label: 'Suggester', keyword: 'suggester', description: 'Post suggestions in #suggestions', color: 0xFBBF24, style: ButtonStyle.Primary },
    ];

    const embed = new EmbedBuilder()
      .setColor(0xA855F7)
      .setTitle('🎭 Pick Your Roles')
      .setDescription([
        '**Click a button below to get or remove a role!**',
        '',
        '🎨 **Artist** — unlocks the art channel ping & Artist tag',
        '💡 **Suggester** — lets you submit suggestions and be notified of updates',
        '',
        '> Click again to remove the role.',
        '',
        `💬 **Discord:** [Join our server](${DISCORD_INVITE})`,
        `🎮 **Roblox Group:** [Join here](${ROBLOX_GROUP})`,
      ].join('\n'))
      .setThumbnail(guild.iconURL({ dynamic: true, size: 256 }))
      .setFooter({ text: `${guild.name} • Click to toggle your role`, iconURL: guild.iconURL({ dynamic: true }) })
      .setTimestamp();

    const row = new ActionRowBuilder();

    for (const roleData of selfRoles) {
      const role = guild.roles.cache.find(r => r.name.toLowerCase().includes(roleData.keyword));
      if (!role) continue;
      row.addComponents(
        new ButtonBuilder()
          .setCustomId(`selfrole_${role.id}`)
          .setLabel(roleData.label)
          .setEmoji(roleData.emoji)
          .setStyle(roleData.style)
      );
    }

    if (row.components.length === 0) {
      await interaction.reply({ content: '❌ No matching roles found! Run `/setup` first.', ephemeral: true });
      return;
    }

    await interaction.channel.send({ embeds: [embed], components: [row] });
    await interaction.reply({ content: '✅ Self-roles embed posted!', ephemeral: true });
  }
};
