The flatpak we publish to flathub tracks the [latest stable release](https://github.com/ZQuestClassic/ZQuestClassic/releases/latest).

To use this flatpak, visit the [Flathub page](https://flathub.org/apps/com.zquestclassic.ZQuest).

# Development

Prevent git lfs from downloading huge test files

> sudo git config --system "includeIf.gitdir:flatpak-builder/git/https_github.com_ZQuestClassic_ZQuestClassic.path" "$PWD/gitconfig.inc"

Build:

> flatpak-builder build com.zquestclassic.ZQuest.yml --force-clean --user --install

Then to run:

> flatpak run com.zquestclassic.ZQuest

# Updating to a new release

flatpak-external-data-checker opens a PR when a new 2.55.x tag is released. That PR only updates the zquest source, so also:

- Set `RELEASE_TAG` in the manifest to the new version.
- Update any dependency sources whose pins changed upstream. The "Check dependency pins" workflow (`.github/check_deps.py`) compares the manifest against upstream's `CMakeLists.txt` and lists what is out of date. Run it locally with `python3 .github/check_deps.py`.
