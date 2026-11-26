REWARDS_URL = "https://rewards.bing.com/"
REWARDS_DASHBOARD_URL = "https://rewards.bing.com/dashboard"
REWARDS_EARN_URL = "https://rewards.bing.com/earn"
REWARDS_QUEST_URL = "https://rewards.bing.com/earn/quest/"
SEARCH_URL = "https://bing.com/search?q=Microsoft+Rewards"

REWARDS_APP_USER_AGENT_MARKER = "MSRewards/Desktop/1.16.0"
"""
What the Microsoft Rewards desktop app appends to its user agent. The server unlocks the
steps of the Rewards App weekly quest for the requests that carry it: the version does not
seem to matter, and the app's extra header and client hints are not needed.
"""
