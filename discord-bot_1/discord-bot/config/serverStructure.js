// config/serverStructure.js
// Defines the full server layout — categories, channels, permissions

module.exports = {
  roles: [
    { name: "👑 Owner",       color: "#FFD700", hoist: true, position: 10 },
    { name: "⚙️ Admin",       color: "#FF4444", hoist: true, position: 9  },
    { name: "🛡️ Moderator",   color: "#FF8C00", hoist: true, position: 8  },
    { name: "💎 Supporter",   color: "#A855F7", hoist: true, position: 7  },
    { name: "🚀 Booster",     color: "#F472B6", hoist: true, position: 6  },
    { name: "✨ Member",      color: "#60A5FA", hoist: true, position: 5  },
    { name: "🎨 Artist",      color: "#34D399", hoist: false, position: 4 },
    { name: "💡 Suggester",   color: "#FBBF24", hoist: false, position: 3 },
    { name: "🤖 Bot",         color: "#94A3B8", hoist: true,  position: 2 },
  ],

  categories: [
    {
      name: "📢 Server Info",
      channels: [
        { name: "👋・welcome",       type: "text",  topic: "Welcome new members!",                  slowmode: 0  },
        { name: "📣・announcements", type: "text",  topic: "Official server announcements.",        slowmode: 0  },
        { name: "🎁・giveaways",     type: "text",  topic: "Giveaways and competitions.",           slowmode: 0  },
        { name: "📅・events",        type: "text",  topic: "Upcoming server events.",               slowmode: 0  },
        { name: "📝・apply",         type: "text",  topic: "Apply for staff or special roles.",     slowmode: 30 },
        { name: "🎭・self-roles",    type: "text",  topic: "React or click to get your own roles.", slowmode: 0  },
      ]
    },
    {
      name: "💎 Supporters",
      supporterOnly: true,
      channels: [
        { name: "✨・access",       type: "text",  topic: "Supporter-only access hub.",   slowmode: 0  },
        { name: "🚀・boosts",       type: "text",  topic: "Boost announcements.",         slowmode: 0  },
        { name: "💎・perks",        type: "text",  topic: "Supporter perks and info.",    slowmode: 0  },
        { name: "👑・vip-chat",     type: "text",  topic: "Exclusive VIP chat.",          slowmode: 5  },
        { name: "🔊・vip-only-vc",  type: "voice", topic: "VIP voice channel.",           slowmode: 0  },
      ]
    },
    {
      name: "💬 Main Channels",
      channels: [
        { name: "💬・general",       type: "text",  topic: "General chat for everyone.",          slowmode: 3  },
        { name: "😂・memes",         type: "text",  topic: "Post your memes here.",               slowmode: 10 },
        { name: "🎨・art",           type: "text",  topic: "Share your artwork. Images only.",    slowmode: 0  },
        { name: "🔢・counting",      type: "text",  topic: "Count as high as possible!",          slowmode: 0  },
        { name: "💡・suggestions",   type: "text",  topic: "Submit your suggestions.",            slowmode: 60 },
        { name: "📣・self-promote",  type: "text",  topic: "Promote your content here.",          slowmode: 300},
        { name: "🤖・bot-commands",  type: "text",  topic: "Use bot commands here.",              slowmode: 0  },
      ]
    },
    {
      name: "🔊 Voice",
      channels: [
        { name: "🔊 General VC",   type: "voice" },
        { name: "🎮 Gaming VC",    type: "voice" },
        { name: "🎵 Music VC",     type: "voice" },
        { name: "📚 Study VC",     type: "voice" },
      ]
    },
    {
      name: "📋 Logs",
      adminOnly: true,
      channels: [
        { name: "📋・mod-log",      type: "text", topic: "Moderation actions log."  },
        { name: "🔍・server-log",   type: "text", topic: "Server events log."       },
        { name: "💬・message-log",  type: "text", topic: "Deleted/edited messages." },
      ]
    }
  ]
};
