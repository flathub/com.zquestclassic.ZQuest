The flatpak we publish to flathub tracks the [latest stable release](https://github.com/ZQuestClassic/ZQuestClassic/releases/latest).

To use this flatpak, visit the [Flathub page](https://flathub.org/apps/com.zquestclassic.ZQuest).

# Development

Prevent git lfs from downloading huge test files

```bash
sudo git config --system "includeIf.gitdir:flatpak-builder/git/https_github.com_ZQuestClassic_ZQuestClassic.path" "$PWD/gitconfig.inc"
```

Build:

```bash
flatpak-builder build com.zquestclassic.ZQuest.yml --force-clean --user --install
```

Then to run:

```bash
flatpak run com.zquestclassic.ZQuest
```
