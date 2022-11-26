# Stranger of Paradise Inventory Filter

This tool will allow you to have better control over how you manage your inventory in Stranger of Paradise: Final Fantasy Origin.

Each item effect can be given a minimum level to keep. If an item has any effect above its minimum level, it will be marked to be kept by locking it using the game's inventory locking feature. After the tool runs, you should be left with many items that you don't care to keep left unlocked, which you can then dismantle at the smithy.

This tool will read the memory of the game's process to get the item details and set item locks. So make sure to have the game running, and your save loaded before running the tool, or it won't work.

## Back Up Your Save

Since this is still an experimental tool, it is a good idea to back up your save before trying it. I've been using it myself and have not encountered any issues, but it's better to be safe than sorry!

Your save file can be found here:

`%USERPROFILE%\Documents\My Games\STRANGER OF PARADISE FINAL FANTASY ORIGIN\EOS\`

You should see a folder with a bunch of letters and numbers in the name. Exit the game, then copy that somewhere else. If you encounter anything strange after running the tool, you can just drop your copy back here.

## How to Configure

See the `config.ini` file included with the release. There are instructions for each section there. An item will be kept if it meets any of the criteria provided.

Note: The `[Effects]` section includes all of the *technically possible* values, as found in the game's data files. Not all of them actually appear on items that drop in the game as of yet. When in doubt, just leave the line commented out by putting a `#` at the beginning of the line.
