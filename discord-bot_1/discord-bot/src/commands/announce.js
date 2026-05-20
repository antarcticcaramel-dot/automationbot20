// src/commands/announce.js
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, ChannelType } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('announce')
    .setDescription('📢 Post a fancy announcement to a specific channel')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages)
    .addChannelOption(o => o
      .setName('channel')
      .setDescription('Channel to post the announcement in')
      .addChannelTypes(ChannelType.GuildText)
      .setRequired(true))
    .addStringOption(o => o.setName('title').setDescription('Announcement title').setRequired(true))
    .addStringOption(o => o.setName('message').setDescription('Announcement content').setRequired(true))
    .addStringOption(o => o.setName('color').setDescription('Embed color').setRequired(false)
      .addChoices(
        { name: '💜 Purple', value: '#A855F7' },
        { name: '💙 Blue',   value: '#3B82F6' },
        { name: '💚 Green',  value: '#22C55E' },
        { name: '❤️ Red',    value: '#EF4444' },
        { name: '🧡 Orange', value: '#F97316' },
        { name: '💛 Yellow', value: '#FBBF24' },
        { name: '💗 Pink',   value: '#F472B6' },
      ))
    .addStringOption(o => o.setName('ping').setDescription('Who to ping?').setRequired(false)
      .addChoices(
        { name: '@ everyone', value: '@everyone' },
        { name: '@ here',     value: '@here' },
        { name: 'No ping',    value: 'none' },
      ))
    .addBooleanOption(o => o
      .setName('pin')
      .setDescription('Pin this announcement in the channel?')
      .setRequired(false)),

  async execute(interaction) {
    const channel = interaction.options.getChannel('channel');
    const title   = interaction.options.getString('title');
    const msg     = interaction.options.getString('message');
    const color   = interaction.options.getString('color') || '#A855F7';
    const ping    = interaction.options.getString('ping') || 'none';
    const pin     = interaction.options.getBoolean('pin') ?? false;

    const embed = new EmbedBuilder()
      .setColor(color)
      .setTitle(`📢 ${title}`)
      .setDescription(msg)
      .setAuthor({
        name: `${interaction.member?.displayName || interaction.user.username}`,
        iconURL: interaction.user.displayAvatarURL({ dynamic: true })
      })
      .setTimestamp()
      .setFooter({ text: interaction.guild.name, iconURL: interaction.guild.iconURL({ dynamic: true }) });

    const content = ping !== 'none' ? ping : undefined;
    const posted = await channel.send({ content, embeds: [embed] });

    if (pin) {
      await posted.pin().catch(() => {});
    }

    await interaction.reply({
      embeds: [new EmbedBuilder()
        .setColor(0x22C55E)
        .setDescription(`✅ Announcement posted in ${channel}${pin ? ' and **pinned**' : ''}!`)
      ],
      ephemeral: true
    });
  }
};
