// src/commands/selfroles.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('selfroles')
    .setDescription('📌 Post the self-roles embed in the current channel')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels),

  async execute(interaction) {
    const guild = interaction.guild;

    // Gather roles that should be self-assignable
    const selfRoles = [
      { emoji: '🎨', label: 'Artist',    description: 'Share your art in #art',         color: 0x34D399 },
      { emoji: '💡', label: 'Suggester', description: 'Post in #suggestions',            color: 0xFBBF24 },
      { emoji: '🎮', label: 'Gamer',     description: 'Gaming pings & channels',         color: 0x60A5FA },
      { emoji: '🎵', label: 'Music Fan', description: 'Music updates & pings',           color: 0xF472B6 },
      { emoji: '📢', label: 'Ping Me',   description: 'Receive event & giveaway pings',  color: 0xA855F7 },
    ];

    const embed = new EmbedBuilder()
      .setColor(0xA855F7)
      .setTitle('🎭 Self Roles')
      .setDescription([
        '**Pick your roles below!**',
        'Click a button to get or remove a role.',
        'You can have as many as you want. ✨',
        '',
        selfRoles.map(r => `${r.emoji} **${r.label}** — ${r.description}`).join('\n'),
      ].join('\n'))
      .setThumbnail(guild.iconURL({ dynamic: true, size: 256 }))
      .setFooter({ text: `${guild.name} • Click to toggle your role`, iconURL: guild.iconURL({ dynamic: true }) })
      .setTimestamp();

    // Build button rows (max 5 per row, max 5 rows)
    const rows = [];
    let currentRow = new ActionRowBuilder();
    let btnCount = 0;

    for (const roleData of selfRoles) {
      // Find or skip role in guild
      const role = guild.roles.cache.find(r =>
        r.name.toLowerCase().includes(roleData.label.toLowerCase())
      );

      if (!role) continue;

      currentRow.addComponents(
        new ButtonBuilder()
          .setCustomId(`selfrole_${role.id}`)
          .setLabel(roleData.label)
          .setEmoji(roleData.emoji)
          .setStyle(ButtonStyle.Secondary)
      );

      btnCount++;
      if (btnCount % 5 === 0) {
        rows.push(currentRow);
        currentRow = new ActionRowBuilder();
      }
    }

    if (currentRow.components.length > 0) rows.push(currentRow);

    if (rows.length === 0) {
      await interaction.reply({
        content: '❌ No matching roles found! Run `/setup` first, then try again.',
        ephemeral: true
      });
      return;
    }

    await interaction.channel.send({ embeds: [embed], components: rows });
    await interaction.reply({ content: '✅ Self-roles embed posted!', ephemeral: true });
  }
};
