The flatpak we publish to flathub tracks the [latest stable release](https://github.com/ZQuestClassic/ZQuestClassic/releases/latest).

To use this flatpak, visit the [Flathub page](https://flathub.org/apps/com.zquestclassic.ZQuest).

# Development

To build locally:

> # prevent git lfs from downloading huge test files
> sudo git config --system "includeIf.gitdir:flatpak-builder/git/https_github.com_ZQuestClassic_ZQuestClassic.path" "$PWD/gitconfig.inc"
>
> flatpak-builder build com.zquestclassic.ZQuest.yml --force-clean --user --install

Then to run:

> flatpak run com.zquestclassic.ZQuest
