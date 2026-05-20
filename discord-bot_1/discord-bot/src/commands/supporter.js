// src/commands/supporter.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('supporter')
    .setDescription('💎 Grant or remove the Supporter role from a member')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageRoles)
    .addUserOption(o => o.setName('user').setDescription('Member to update').setRequired(true))
    .addStringOption(o => o.setName('action').setDescription('Give or remove').setRequired(true)
      .addChoices(
        { name: '✅ Give Supporter', value: 'give' },
        { name: '❌ Remove Supporter', value: 'remove' },
      )),

  async execute(interaction) {
    const target = interaction.options.getMember('user');
    const action = interaction.options.getString('action');
    const guild  = interaction.guild;

    const supporterRole = guild.roles.cache.find(r => r.name.toLowerCase().includes('supporter'));
    if (!supporterRole) {
      await interaction.reply({ content: '❌ Supporter role not found! Run `/setup` first.', ephemeral: true });
      return;
    }

    if (action === 'give') {
      await target.roles.add(supporterRole);

      // Welcome them in the supporters access channel
      const accessCh = guild.channels.cache.find(c => c.name.includes('access') && c.isTextBased());
      if (accessCh) {
        await accessCh.send({
          embeds: [new EmbedBuilder()
            .setColor(0xA855F7)
            .setTitle('💎 New Supporter!')
            .setDescription(`Welcome ${target} to the **Supporters** family! 💜\nThank you so much for your support — enjoy your exclusive perks!`)
            .setThumbnail(target.user.displayAvatarURL({ dynamic: true }))
            .setTimestamp()
            .setFooter({ text: guild.name, iconURL: guild.iconURL({ dynamic: true }) })
          ]
        });
      }

      await interaction.reply({
        embeds: [new EmbedBuilder().setColor(0x22C55E).setDescription(`✅ Gave **Supporter** to ${target}.`)],
        ephemeral: true
      });

    } else {
      // Remove supporter role — and also booster role if they have it
      const boosterRole = guild.roles.cache.find(r => r.name.toLowerCase().includes('booster') && !r.managed);
      await target.roles.remove(supporterRole).catch(() => {});
      if (boosterRole && target.roles.cache.has(boosterRole.id)) {
        await target.roles.remove(boosterRole).catch(() => {});
      }

      // DM the user so they know
      try {
        await target.send({
          embeds: [new EmbedBuilder()
            .setColor(0xEF4444)
            .setTitle('💎 Supporter Role Removed')
            .setDescription(`Your **Supporter** role in **${guild.name}** has been removed.\nIf you think this is a mistake, please contact a staff member.`)
            .setTimestamp()
          ]
        });
      } catch {}

      await interaction.reply({
        embeds: [new EmbedBuilder().setColor(0xEF4444).setDescription(`✅ Removed **Supporter** (and Booster if applicable) from ${target}.`)],
        ephemeral: true
      });
    }
  }
};
