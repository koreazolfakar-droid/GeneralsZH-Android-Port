// GeneralsX @bugfix Codex 05/10/2026 Synthetic localization fixtures; no retail/mod data bundled.
// Included after the production GameText.cpp by test-mod-localization.py.
const Char* g_strFile = "data/%s/generals.str";
const Char* g_csfFile = "data/%s/generals.csf";

static void put32(std::vector<unsigned char>& bytes, uint32_t value)
{
    for (int i = 0; i < 4; ++i) bytes.push_back(value >> (8 * i));
}

static std::vector<unsigned char> csf(std::initializer_list<std::pair<std::string, std::wstring>> labels)
{
    std::vector<unsigned char> bytes;
    for (auto value : {uint32_t(CSF_ID), 3u, uint32_t(labels.size()), uint32_t(labels.size()), 0u, 0u})
        put32(bytes, value);
    for (const auto& label : labels) {
        put32(bytes, CSF_LABEL);
        put32(bytes, 1);
        put32(bytes, label.first.size());
        bytes.insert(bytes.end(), label.first.begin(), label.first.end());
        put32(bytes, CSF_STRING);
        put32(bytes, label.second.size());
        for (auto character : label.second) {
            uint16_t inverted = ~uint16_t(character);
            bytes.push_back(inverted);
            bytes.push_back(inverted >> 8);
        }
    }
    return bytes;
}

static std::vector<unsigned char> str(const char* text)
{
    return {text, text + strlen(text)};
}

static void expect(GameTextManager& text, const char* label, const wchar_t* value)
{
    Bool exists = false;
    const auto actual = text.fetch(label, &exists);
    if (!exists || actual.s != value) {
        fprintf(stderr, "FAIL: %s expected='%ls' actual='%ls'\n", label, value, actual.str());
        std::abort();
    }
}

int main(int argc, char** argv)
{
    ArchiveFile vanilla;
    vanilla.name = "/game/EnglishZH.big";
    vanilla.entries[key("Data/English/Generals.csf")] = csf({
        {"GUI:Faction", L"Vanilla Army"}, {"GUI:OnlyBase", L"Base fallback"}});
    ArchiveFile mod;
    mod.name = "/game/Mods/TestMod/mod.big";
    mod.entries[key("Data/English/Generals.csf")] = csf({
        {"GUI:Faction", L"Mod Army"}, {"GUI:OnlyMod", L"Mod-only Army"}});
    const auto vanillaStr = str("GUI:Faction\n\"Vanilla translation\"\nEND\n"
                                "GUI:OnlyBase\n\"Translated base\"\nEND\n");
    lfs.entries[key("data/english/generals.str")] = vanillaStr;

    if (argc > 1 && std::string(argv[1]) == "before") {
        afs.archives = {&mod, &vanilla};
        gd.m_modDir = "/game/Mods/TestMod";
        GameTextManager text;
        text.init();
        expect(text, "GUI:Faction", L"Vanilla translation");
        assert(text.fetch("GUI:OnlyMod").s.find(L"MISSING:") == 0);
        puts("PASS: unmodified production loader reproduces STR masking mod CSF");
        return 0;
    }

    // Vanilla -> Mod -> Vanilla using one manager with full deinit/init, then a new
    // manager with the mod active. This checks text cache cleanup; not Android lifecycle.
    GameTextManager text;
    afs.archives = {&vanilla};
    text.init();
    expect(text, "GUI:Faction", L"Vanilla translation");
    text.deinit();
    afs.archives = {&mod, &vanilla};
    gd.m_modDir = "/game/Mods/TestMod";
    text.init();
    expect(text, "GUI:Faction", L"Mod Army");
    expect(text, "GUI:OnlyMod", L"Mod-only Army");
    expect(text, "GUI:OnlyBase", L"Base fallback");
    text.deinit();
    afs.archives = {&vanilla};
    gd.m_modDir = "";
    text.init();
    expect(text, "GUI:Faction", L"Vanilla translation");
    Bool exists = true;
    text.fetch("GUI:OnlyMod", &exists);
    assert(!exists);
    text.deinit();
    afs.archives = {&mod, &vanilla};
    gd.m_modDir = "/game/Mods/TestMod";
    { GameTextManager restarted; restarted.init(); expect(restarted, "GUI:Faction", L"Mod Army"); }
    puts("PASS: fixture Vanilla -> Mod -> Vanilla and restart with mod; no stale labels");

    // A loose Vanilla CSF must not hide the active mod archive; instances account
    // for the loose entry, and the next CSF is still the mounted base fallback.
    lfs.entries[key("data/english/generals.csf")] = csf({{"GUI:Faction", L"Loose base Army"}, {"GUI:OnlyBase", L"Loose base fallback"}});
    text.init();
    expect(text, "GUI:Faction", L"Mod Army");
    expect(text, "GUI:OnlyBase", L"Loose base fallback");
    text.deinit();
    lfs.entries.erase(key("data/english/generals.csf"));
    puts("PASS: active archive bypasses loose Vanilla CSF and STR");

    gd.m_modDir = "";
    gd.m_modBIG = "/game/Mods/TestMod/mod.big";
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: single -mod BIG ownership");

    gd.m_modBIG = "";
    gd.m_modDir = "\\GAME\\MODS\\TESTMOD\\";
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: case, Windows separators and trailing separator");

    gd.m_modDir = "/game/Mods/Test";
    text.init(); expect(text, "GUI:Faction", L"Vanilla translation"); text.deinit();
    puts("PASS: sibling prefix is not active-mod ownership");

    gd.m_modDir = "/game/Mods/TestMod";
    afs.archives = {&vanilla};
    text.init(); expect(text, "GUI:Faction", L"Vanilla translation"); text.deinit();
    puts("PASS: active mod without text keeps Vanilla STR priority");

    afs.archives = {&mod, &vanilla};
    setenv("GENERALSX_TEXT_LANGUAGE", "arabic", 1);
    lfs.entries[key("data/arabic/generals.str")] = vanillaStr;
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: English mod table fallback when selected language is not supplied by mod");

    mod.entries[key("data/arabic/generals.csf")] = csf({{"GUI:Faction", L"جيش المود"}});
    text.init(); expect(text, "GUI:Faction", L"جيش المود"); text.deinit();
    puts("PASS: selected-language mod CSF and Unicode names precede mod English");
    unsetenv("GENERALSX_TEXT_LANGUAGE");

    mod.entries[key("data/english/generals.str")] = str("GUI:Faction\n\"Mod STR Army\"\nEND\n");
    text.init(); expect(text, "GUI:Faction", L"Mod STR Army"); text.deinit();
    puts("PASS: mod STR precedes mod CSF and loose Vanilla STR");
    mod.entries.erase(key("data/english/generals.str"));

    const auto modCsf = mod.entries[key("data/english/generals.csf")];
    mod.entries[key("data/english/generals.csf")] = csf({});
    text.init(); expect(text, "GUI:Faction", L"Vanilla translation"); text.deinit();
    mod.entries[key("data/english/generals.csf")] = modCsf;
    puts("PASS: empty mod CSF does not suppress readable Vanilla STR");

    // Original Vanilla CSF-only path remains valid, including arbitrary source names.
    afs.archives = {&vanilla};
    gd.m_modDir = "";
    lfs.entries.clear();
    text.init(); expect(text, "GUI:Faction", L"Vanilla Army"); text.deinit();
    puts("PASS: Vanilla CSF-only installation");

    // GeneralsX @bugfix Codex 08/10/2026 Sources preceding the mod reproduce
    // the first-instance regression; mount order must not be changed to fix it.
    ArchiveFile translation;
    translation.name = "/game/000_Translation.big";
    translation.entries[key("data/english/generals.str")] = vanillaStr;
    gd.m_modDir = "/game/Mods/TestMod";
    afs.archives = {&translation, &vanilla, &mod};
    text.init();
    expect(text, "GUI:Faction", L"Mod Army");
    expect(text, "GUI:OnlyBase", L"Base fallback");
    text.deinit();
    puts("PASS: 3. Vanilla/translation archives before mod do not hide mod names");
    text.init();
    TheGameText = &text;
    INI displayName{"GUI:Faction"};
    UnicodeString translated;
    INI::parseAndTranslateLabel(&displayName, nullptr, &translated, nullptr);
    assert(translated.s == L"Mod Army");
    TheGameText = nullptr;
    text.deinit();
    puts("PASS: real INI DisplayName translation callback receives the mod label");

    lfs.entries[key("data/english/generals.str")] = vanillaStr;
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: 4. Loose Vanilla STR cannot hide a later-instance mod CSF");

    ArchiveFile gameplay;
    gameplay.name = "/game/Mods/TestMod/Gameplay.big";
    gameplay.entries[key("data/ini/object.ini")] = str("fixture");
    afs.archives = {&gameplay, &translation, &vanilla, &mod};
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: 7. Directory mod localization in a later BIG");

    gd.m_modDir = "";
    gd.m_modBIG = mod.name;
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: 8. Direct BIG with preceding translation archives");

    ArchiveFile otherMod;
    otherMod.name = "/game/Mods/TestMod/Other.big";
    otherMod.entries[key("data/english/generals.csf")] = csf({{"GUI:OnlyBase", L"Wrong mod fallback"}});
    gd.m_modBIG = "";
    gd.m_modDir = "/game/Mods/TestMod";
    afs.archives = {&mod, &otherMod, &vanilla};
    text.init();
    expect(text, "GUI:Faction", L"Mod Army");
    expect(text, "GUI:OnlyBase", L"Base fallback");
    text.deinit();
    puts("PASS: 6. Incomplete mod CSF uses Vanilla missing labels, not a second mod BIG");

    afs.archives = {&translation, &vanilla, &mod};
    mod.entries.erase(key("data/arabic/generals.csf"));
    setenv("GENERALSX_TEXT_LANGUAGE", "arabic", 1);
    lfs.entries[key("data/arabic/generals.str")] = vanillaStr;
    text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    puts("PASS: 5. Non-English selected language falls back to mod English");

    mod.entries[key("data/english/generals.str")] = str("GUI:Faction\n\"Wrong English STR\"\nEND\n");
    mod.entries[key("data/arabic/generals.csf")] = csf({{"GUI:Faction", L"فصيل المود"}});
    text.init(); expect(text, "GUI:Faction", L"فصيل المود"); text.deinit();
    puts("PASS: requested-language CSF outranks mod English STR");
    mod.entries[key("data/arabic/generals.str")] = str("GUI:Faction\n\"جيش Рх\"\nEND\n");
    text.init();
    expect(text, "GUI:Faction", L"جيش Рх");
    expect(text, "GUI:OnlyBase", L"Base fallback");
    text.deinit();
    puts("PASS: requested-language UTF-8 STR outranks CSF; missing labels use Vanilla");
    mod.entries.erase(key("data/english/generals.str"));
    mod.entries.erase(key("data/arabic/generals.str"));
    const auto looseEnglish = key("/game/Mods/TestMod/data/english/generals.str");
    lfs.entries[looseEnglish] = str("GUI:Faction\n\"Wrong loose English STR\"\nEND\n");
    text.init(); expect(text, "GUI:Faction", L"فصيل المود"); text.deinit();
    lfs.entries.erase(looseEnglish);
    puts("PASS: requested-language archived CSF outranks loose mod English STR");
    unsetenv("GENERALSX_TEXT_LANGUAGE");
    mod.entries.erase(key("data/arabic/generals.csf"));

    const auto savedEntries = mod.entries;
    for (const char* path : {"data/generals.csf", "generals.csf", "data/generals.str", "generals.str"}) {
        mod.entries.clear();
        mod.entries[key(path)] = std::string(path).find(".csf") != std::string::npos
            ? csf({{"GUI:Faction", L"Layout Army"}}) : str("GUI:Faction\n\"Layout Army\"\nEND\n");
        text.init();
        expect(text, "GUI:Faction", L"Layout Army");
        expect(text, "GUI:OnlyBase", L"Base fallback");
        text.deinit();
    }
    mod.entries = savedEntries;
    puts("PASS: alternate Data and root STR/CSF layouts retain missing-label fallback");

    // No Vanilla CSF: missing mod labels can still use the supported base STR.
    afs.archives = {&mod};
    text.init(); expect(text, "GUI:Faction", L"Mod Army");
    expect(text, "GUI:OnlyBase", L"Translated base"); text.deinit();
    puts("PASS: incomplete mod CSF falls back to Vanilla STR when no base CSF exists");

    afs.archives = {&translation, &vanilla, &mod};
    text.init();
    lfs.entries[key("maps/test/map.str")] = str("GUI:MapOnly\n\"خريطة Мод\"\nEND\nGUI:Faction\n\"Map override\"\nEND\nGUI:OnlyBase\n\"Map base label\"\nEND\n");
    text.initMapStringFile("maps/test/map.str");
    expect(text, "GUI:MapOnly", L"خريطة Мод");
    expect(text, "GUI:Faction", L"Mod Army");
    expect(text, "GUI:OnlyBase", L"Map base label");
    text.reset();
    text.fetch("GUI:MapOnly", &exists); assert(!exists);
    text.deinit();
    puts("PASS: 10. Map STR lookup, UTF-8, existing priority and reset unchanged");

    // Multiple complete reinitializations, including the normal Vanilla CSF-only path.
    lfs.entries.clear();
    for (int i = 0; i < 3; ++i) {
        gd.m_modDir = ""; afs.archives = {&vanilla};
        text.init(); expect(text, "GUI:Faction", L"Vanilla Army");
        text.fetch("GUI:OnlyMod", &exists); assert(!exists); text.deinit();
        gd.m_modDir = "/game/Mods/TestMod"; afs.archives = {&translation, &vanilla, &mod};
        text.init(); expect(text, "GUI:Faction", L"Mod Army"); text.deinit();
    }
    gd.m_modDir = ""; afs.archives = {&vanilla};
    { GameTextManager restarted; restarted.init(); expect(restarted, "GUI:Faction", L"Vanilla Army"); }
    puts("PASS: 1/2/9. Vanilla names and Mod/Vanilla reinitialization/restart without stale labels");

    puts("PASS: all production GameText fixture regression cases");
}
