// src/commands/rules.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('rules')
    .setDescription('📜 Post the server rules embed')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels),

  async execute(interaction) {
    const guild = interaction.guild;

    const embed = new EmbedBuilder()
      .setColor(0xA855F7)
      .setTitle(`📜 ${guild.name} — Server Rules`)
      .setDescription('Please read and follow these rules to keep our community friendly and safe.')
      .addFields(
        { name: '1️⃣  Be Respectful', value: 'Treat everyone with kindness. No harassment, hate speech, or bullying of any kind.' },
        { name: '2️⃣  No Spam', value: 'No excessive messages, repeated text, or flooding any channel.' },
        { name: '3️⃣  Stay On Topic', value: 'Keep messages relevant to the channel you\'re posting in.' },
        { name: '4️⃣  No NSFW Content', value: 'Keep all content SFW (safe for work). NSFW content will result in an immediate ban.' },
        { name: '5️⃣  No Self-Promotion Without Permission', value: 'Only post self-promo in <#self-promote>. Do not DM members unsolicited.' },
        { name: '6️⃣  Follow Discord ToS', value: 'You must follow [Discord\'s Terms of Service](https://discord.com/terms) at all times.' },
        { name: '7️⃣  Listen to Staff', value: 'Moderators and admins have final say. Respect their decisions.' },
        { name: '8️⃣  Use Common Sense', value: 'If something seems like it might break the rules, it probably does.' },
      )
      .setThumbnail(guild.iconURL({ dynamic: true, size: 256 }))
      .setImage(guild.bannerURL({ size: 1024 }) || null)
      .setTimestamp()
      .setFooter({ text: `${guild.name} • Breaking rules may result in a mute, kick, or ban.`, iconURL: guild.iconURL({ dynamic: true }) });

    await interaction.channel.send({ embeds: [embed] });
    await interaction.reply({ content: '✅ Rules posted!', ephemeral: true });
  }
};
