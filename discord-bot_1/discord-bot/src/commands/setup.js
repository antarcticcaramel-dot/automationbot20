// src/commands/setup.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, ChannelType } = require('discord.js');
const structure = require('../../config/serverStructure');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('setup')
    .setDescription('🔧 Auto-setup the entire server structure (channels, roles, categories)')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });
    const guild = interaction.guild;
    const log = [];

    try {
      // ── 1. Create Roles ─────────────────────────────────────────────────────
      log.push('**Creating roles...**');
      const createdRoles = {};

      for (const roleData of structure.roles) {
        const existing = guild.roles.cache.find(r => r.name === roleData.name);
        if (!existing) {
          const role = await guild.roles.create({
            name: roleData.name,
            color: roleData.color,
            hoist: roleData.hoist,
            mentionable: false,
            reason: 'Bot setup'
          });
          createdRoles[roleData.name] = role;
          log.push(`✅ Created role: ${role.name}`);
        } else {
          createdRoles[roleData.name] = existing;
          log.push(`⏭️ Role exists: ${existing.name}`);
        }
      }

      // ── 2. Create Categories & Channels ────────────────────────────────────
      log.push('\n**Creating categories & channels...**');

      const supporterRole = Object.values(createdRoles).find(r => r.name.includes('Supporter'));
      const adminRole     = Object.values(createdRoles).find(r => r.name.includes('Admin'));
      const everyoneRole  = guild.roles.everyone;

      for (const cat of structure.categories) {
        // Check if category exists
        let category = guild.channels.cache.find(
          c => c.type === ChannelType.GuildCategory && c.name.toLowerCase().includes(
            cat.name.replace(/[^a-zA-Z ]/g, '').trim().toLowerCase()
          )
        );

        // Build permission overwrites
        const overwrites = [];

        if (cat.adminOnly) {
          overwrites.push(
            { id: everyoneRole.id, deny: ['ViewChannel'] },
            ...(adminRole ? [{ id: adminRole.id, allow: ['ViewChannel'] }] : [])
          );
        } else if (cat.supporterOnly) {
          overwrites.push(
            { id: everyoneRole.id, deny: ['ViewChannel'] },
            ...(supporterRole ? [{ id: supporterRole.id, allow: ['ViewChannel'] }] : [])
          );
        }

        if (!category) {
          category = await guild.channels.create({
            name: cat.name,
            type: ChannelType.GuildCategory,
            permissionOverwrites: overwrites,
            reason: 'Bot setup'
          });
          log.push(`📁 Created category: ${cat.name}`);
        } else {
          log.push(`⏭️ Category exists: ${cat.name}`);
        }

        // Create channels inside category
        for (const ch of cat.channels) {
          const cleanName = ch.name.replace(/[^a-zA-Z0-9\-・]/g, '').toLowerCase();
          const existing = guild.channels.cache.find(
            c => c.parentId === category.id && c.name.includes(cleanName.split('・')[1] || cleanName)
          );

          if (!existing) {
            const channelType = ch.type === 'voice' ? ChannelType.GuildVoice : ChannelType.GuildText;
            const created = await guild.channels.create({
              name: ch.name,
              type: channelType,
              parent: category.id,
              topic: ch.topic || null,
              rateLimitPerUser: ch.slowmode || 0,
              reason: 'Bot setup'
            });
            log.push(`  ✅ ${ch.type === 'voice' ? '🔊' : '#'} ${created.name}`);
          } else {
            log.push(`  ⏭️ Exists: ${ch.name}`);
          }
          // Small delay to avoid rate limits
          await new Promise(r => setTimeout(r, 300));
        }
      }

      // ── 3. Summary ──────────────────────────────────────────────────────────
      const summaryEmbed = new EmbedBuilder()
        .setColor(0x22C55E)
        .setTitle('✅ Server Setup Complete!')
        .setDescription('Your server has been fully configured. Run `/selfroles` and `/rules` to finish setup.')
        .addFields(
          { name: '📁 Categories', value: `${structure.categories.length} created`, inline: true },
          { name: '💬 Channels', value: `${structure.categories.reduce((a,c) => a + c.channels.length, 0)} created`, inline: true },
          { name: '🎭 Roles', value: `${structure.roles.length} created`, inline: true },
        )
        .setTimestamp();

      await interaction.editReply({ embeds: [summaryEmbed] });

    } catch (err) {
      console.error('Setup error:', err);
      await interaction.editReply({ content: `❌ Setup failed: ${err.message}` });
    }
  }
};
