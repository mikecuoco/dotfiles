"""Tests for profile loading and composition."""
import pytest
from pathlib import Path

from dotfiles import RESOURCES_DIR
from dotfiles.profiles import load_profiles, resolve_links, LinkSpec


@pytest.fixture()
def profiles():
    return load_profiles(RESOURCES_DIR)


def test_load_profiles_returns_all_expected(profiles):
    expected = {"common", "macos", "linux", "cluster", "codeocean", "codespace"}
    assert expected.issubset(set(profiles.keys()))


def test_common_has_links(profiles):
    assert len(profiles["common"].links) > 0


def test_profile_inherits_field(profiles):
    assert "common" in profiles["macos"].inherits
    assert "linux" in profiles["cluster"].inherits


def test_resolve_common_links(profiles):
    links = resolve_links("common", profiles)
    dsts = [l.dst for l in links]
    assert ".bashrc" in dsts
    assert ".bash_profile" in dsts
    assert ".gitconfig" in dsts
    assert ".claude/CLAUDE.md" in dsts
    assert ".codex/AGENTS.md" in dsts
    assert ".codex/config.toml" in dsts


def test_macos_inherits_common(profiles):
    common_links = {l.dst for l in resolve_links("common", profiles)}
    macos_links  = {l.dst for l in resolve_links("macos", profiles)}
    # macOS should include everything from common
    assert common_links.issubset(macos_links)
    # plus its own overlays
    assert ".aliases.macos" in macos_links
    assert ".exports.macos" in macos_links
    assert ".matplotlib/stylelib" in macos_links


def test_linux_profiles_install_matplotlib_styles(profiles):
    for name in ("linux", "cluster", "codeocean", "codespace"):
        links = {link.dst: link for link in resolve_links(name, profiles)}
        stylelib = links[".config/matplotlib/stylelib"]
        assert stylelib.src == "common/matplotlib/stylelib"


def test_cluster_inherits_linux_and_common(profiles):
    common_links = {l.dst for l in resolve_links("common", profiles)}
    cluster_links = {l.dst for l in resolve_links("cluster", profiles)}
    assert common_links.issubset(cluster_links)
    assert ".exports.linux" in cluster_links
    assert ".exports.cluster" in cluster_links
    assert ".Rprofile" in cluster_links


def test_no_duplicate_dsts(profiles):
    """Each dst should appear at most once — append-mode entries share a dst
    with the base link, but resolve_links returns them separately (base + appends),
    so we check only the link-mode (base) entries for uniqueness."""
    for name in profiles:
        links = resolve_links(name, profiles)
        base_dsts = [l.dst for l in links if l.mode == "link"]
        assert len(base_dsts) == len(set(base_dsts)), (
            f"Duplicate link-mode dst in profile '{name}': {base_dsts}"
        )


def test_codeocean_claude_md_is_append(profiles):
    """codeocean profile should append its CLAUDE.md rather than overwrite common's."""
    links = resolve_links("codeocean", profiles)
    claude_links = [l for l in links if l.dst == ".claude/CLAUDE.md"]
    # shared base, Claude supplement, then shared Code Ocean overlay
    assert len(claude_links) == 3
    assert claude_links[0].mode == "link"
    assert claude_links[1].mode == "append"
    assert claude_links[2].mode == "append"
    assert claude_links[0].src == "common/agents/PREFERENCES.md"
    assert claude_links[1].src == "common/claude/CLAUDE.md"
    assert claude_links[2].src == "codeocean/agents/PREFERENCES.md"


def test_codeocean_codex_agents_is_append(profiles):
    links = resolve_links("codeocean", profiles)
    codex_links = [link for link in links if link.dst == ".codex/AGENTS.md"]

    assert [link.mode for link in codex_links] == ["link", "append", "append"]
    assert codex_links[0].src == "common/agents/PREFERENCES.md"
    assert codex_links[1].src == "common/codex/AGENTS.md"
    assert codex_links[2].src == "codeocean/agents/PREFERENCES.md"


def test_codex_preferences_are_merged(profiles):
    for name in profiles:
        links = resolve_links(name, profiles)
        config = [link for link in links if link.dst == ".codex/config.toml"]
        assert len(config) == 1
        assert config[0].mode == "merge-toml"
        assert config[0].src == "common/codex/preferences.toml"


def test_codeocean_global_claude_defaults_are_merged(profiles):
    links = resolve_links("codeocean", profiles)
    global_links = [link for link in links if link.dst == ".claude.json"]

    assert len(global_links) == 1
    assert global_links[0].mode == "merge-json"
    assert global_links[0].src == "codeocean/claude/global.json"


def test_global_claude_defaults_are_codeocean_only(profiles):
    for name in profiles:
        links = resolve_links(name, profiles)
        has_global_defaults = any(link.dst == ".claude.json" for link in links)
        assert has_global_defaults is (name == "codeocean")


def test_append_mode_concat(tmp_path):
    """The installer should compose both agents' Code Ocean instructions."""
    from dotfiles.install import run_install

    ok = run_install(profile="codeocean", dry_run=False, home=tmp_path)
    assert ok is True
    claude_md = tmp_path / ".claude" / "CLAUDE.md"
    assert claude_md.exists()
    assert not claude_md.is_symlink()          # generated file, not symlink
    content = claude_md.read_text()
    assert "Working style" in content       # from common global
    assert "Code Ocean" in content          # from codeocean append

    codex_md = tmp_path / ".codex" / "AGENTS.md"
    assert codex_md.exists()
    assert not codex_md.is_symlink()
    codex_content = codex_md.read_text()
    assert "Working style" in codex_content
    assert "Codex delegation" in codex_content
    assert "Code Ocean" in codex_content


def test_unknown_profile_raises(profiles):
    with pytest.raises(ValueError, match="Unknown profile"):
        resolve_links("doesnotexist", profiles)


def test_invalid_mode_raises(tmp_path):
    """A typo in mode should raise ValueError at load time, not silently become a base link."""
    toml = tmp_path / "profiles.toml"
    toml.write_text(
        '[profiles.bad]\ndescription = ""\ninherits = []\n'
        'links = [{ src = "common/shell/.bashrc", dst = ".bashrc", mode = "apend" }]\n'
    )
    with pytest.raises(ValueError, match="invalid mode"):
        load_profiles(tmp_path)


def test_append_without_base_raises(tmp_path):
    """An append link with no base link for the same dst should raise at resolve time."""
    toml = tmp_path / "profiles.toml"
    toml.write_text(
        '[profiles.orphan]\ndescription = ""\ninherits = []\n'
        'links = [{ src = "common/claude/CLAUDE.md", dst = ".claude/CLAUDE.md", mode = "append" }]\n'
    )
    profs = load_profiles(tmp_path)
    with pytest.raises(ValueError, match="no base link"):
        resolve_links("orphan", profs)


def test_merge_json_cannot_share_a_link_destination(tmp_path):
    toml = tmp_path / "profiles.toml"
    toml.write_text(
        '[profiles.bad]\ndescription = ""\ninherits = []\n'
        'links = ['
        '{ src = "base.json", dst = ".config.json" },'
        '{ src = "overlay.json", dst = ".config.json", mode = "merge-json" }'
        ']\n'
    )
    profs = load_profiles(tmp_path)

    with pytest.raises(ValueError, match="also use link/append"):
        resolve_links("bad", profs)


def test_merge_toml_cannot_share_a_link_destination(tmp_path):
    toml = tmp_path / "profiles.toml"
    toml.write_text(
        '[profiles.bad]\ndescription = ""\ninherits = []\n'
        'links = ['
        '{ src = "base.toml", dst = ".config.toml" },'
        '{ src = "overlay.toml", dst = ".config.toml", mode = "merge-toml" }'
        ']\n'
    )
    profs = load_profiles(tmp_path)

    with pytest.raises(ValueError, match="also use link/append"):
        resolve_links("bad", profs)


def test_all_sources_exist(profiles):
    """Every link source referenced in profiles.toml must exist on disk."""
    missing = []
    for name in profiles:
        for link in resolve_links(name, profiles):
            src = RESOURCES_DIR / link.src
            if not src.exists():
                missing.append(f"{name}: {link.src}")
    assert not missing, f"Missing resource files:\n" + "\n".join(missing)
