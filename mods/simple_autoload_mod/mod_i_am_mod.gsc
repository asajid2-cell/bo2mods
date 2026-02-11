init()
{
    start_mod();
}

main()
{
    // Fallback entry point in case this map uses main() instead of init().
    start_mod();
}

start_mod()
{
    if ( isdefined( level.simple_wonder_mod_started ) )
        return;

    level.simple_wonder_mod_started = 1;
    level thread on_player_connect();
}

on_player_connect()
{
    for (;;)
    {
        level waittill("connected", player);
        player thread on_player_spawn();
    }
}

on_player_spawn()
{
    self endon("disconnect");

    for (;;)
    {
        self waittill("spawned_player");
        wait 0.8;

        if ( !is_zombies_map() )
            continue;

        if ( !isdefined( self.mod_loadout_options ) || self.mod_loadout_options.size < 3 )
            self.mod_loadout_options = generate_loadout_options();

        if ( !isdefined( self.mod_selected_loadout ) )
            self.mod_selected_loadout = self show_loadout_picker( self.mod_loadout_options );

        if ( !isdefined( self.mod_selected_loadout ) )
            self.mod_selected_loadout = 0;

        if ( self.mod_selected_loadout < 0 || self.mod_selected_loadout >= self.mod_loadout_options.size )
            self.mod_selected_loadout = 0;

        self apply_selected_loadout( self.mod_loadout_options[self.mod_selected_loadout] );
    }
}

is_zombies_map()
{
    if ( isdefined( level.zombiemode ) && level.zombiemode )
        return true;

    return false;
}

generate_loadout_options()
{
    weapon_pool = build_weapon_pool();
    melee_pool = build_melee_pool();
    perk_pool = build_perk_pool();
    class_catalog = build_class_catalog();
    selected_classes = pick_random_class_themes( class_catalog, 3 );
    used_weapons = [];
    loadouts = [];

    for ( i = 0; i < selected_classes.size && loadouts.size < 3; i++ )
    {
        class_theme = selected_classes[i];
        loadout = spawnstruct();
        loadout.class_theme = class_theme;
        loadout.weapons = build_themed_weapons( weapon_pool, class_theme.weapon_tags, 3, used_weapons );

        for ( w = 0; w < loadout.weapons.size; w++ )
            used_weapons = add_unique( used_weapons, loadout.weapons[w] );

        melee_pick = build_themed_melee( melee_pool, class_theme.melee_tags );

        if ( !isdefined( melee_pick ) || melee_pick == "" )
            loadout.melee = "knife_zm";
        else
            loadout.melee = melee_pick;

        loadout.perks = build_random_perk_set( perk_pool );
        loadouts[loadouts.size] = loadout;
    }

    while ( loadouts.size < 3 )
    {
        loadout = spawnstruct();
        loadout.class_theme = build_default_class_theme();
        loadout.weapons = build_themed_weapons( weapon_pool, loadout.class_theme.weapon_tags, 3, used_weapons );
        loadout.melee = build_themed_melee( melee_pool, loadout.class_theme.melee_tags );
        loadout.perks = build_random_perk_set( perk_pool );
        loadouts[loadouts.size] = loadout;
    }

    return loadouts;
}

build_class_catalog()
{
    catalog = [];

    catalog[catalog.size] = create_class_theme( "NEON REAPER", "SMG RUSH PACKAGE", make_tag_array( "smg", "uzi", "vector", "msmc", "mp5", "pdw" ), make_tag_array( "knife", "galva", "tazer", "", "", "" ), ( 0.06, 0.10, 0.17 ), ( 0.10, 0.20, 0.30 ), ( 0.22, 0.86, 1.00 ), ( 0.62, 0.93, 1.00 ), ( 1.00, 0.56, 0.56 ), ( 0.86, 0.68, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "IRON SENTINEL", "LMG SUPPRESSION KIT", make_tag_array( "lmg", "hamr", "lsat", "mk48", "qbb", "rpd" ), make_tag_array( "knife", "bowie", "", "", "", "" ), ( 0.10, 0.11, 0.13 ), ( 0.18, 0.19, 0.22 ), ( 0.85, 0.84, 0.74 ), ( 0.83, 0.90, 0.98 ), ( 1.00, 0.62, 0.46 ), ( 0.84, 0.75, 0.97 ) );
    catalog[catalog.size] = create_class_theme( "VOID SNIPER", "LONG RANGE EXECUTIONER", make_tag_array( "sniper", "dsr", "ballista", "svu", "xpr", "falsniper" ), make_tag_array( "knife", "sickle", "", "", "", "" ), ( 0.05, 0.05, 0.10 ), ( 0.11, 0.11, 0.18 ), ( 0.64, 0.65, 1.00 ), ( 0.72, 0.88, 1.00 ), ( 1.00, 0.58, 0.58 ), ( 0.88, 0.72, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "HELLFORGE", "SHOTGUN BREACH LOADOUT", make_tag_array( "shotgun", "m1216", "870", "s12", "ksg", "remington" ), make_tag_array( "bowie", "knife", "", "", "", "" ), ( 0.14, 0.07, 0.07 ), ( 0.24, 0.12, 0.10 ), ( 1.00, 0.46, 0.20 ), ( 1.00, 0.78, 0.56 ), ( 1.00, 0.50, 0.50 ), ( 0.92, 0.70, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "ARCANE RELIC", "WONDER WEAPON HUNTER", make_tag_array( "ray", "mark2", "staff", "paralyzer", "sliquifier", "blundergat" ), make_tag_array( "galva", "tazer", "knife", "", "", "" ), ( 0.07, 0.08, 0.19 ), ( 0.13, 0.14, 0.30 ), ( 0.58, 0.72, 1.00 ), ( 0.70, 0.92, 1.00 ), ( 1.00, 0.58, 0.54 ), ( 0.84, 0.70, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "RAIL DEMON", "EXPLOSIVE PAYLOAD", make_tag_array( "launcher", "war", "rpg", "m32", "crossbow", "china" ), make_tag_array( "knife", "sickle", "", "", "", "" ), ( 0.12, 0.08, 0.06 ), ( 0.22, 0.14, 0.11 ), ( 1.00, 0.72, 0.22 ), ( 1.00, 0.90, 0.62 ), ( 1.00, 0.54, 0.46 ), ( 0.90, 0.75, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "PLAGUE DOCTOR", "TOXIC EXPERIMENTAL KIT", make_tag_array( "sliquifier", "acid", "blundergat", "executioner", "five", "fiveseven" ), make_tag_array( "knife", "bowie", "", "", "", "" ), ( 0.06, 0.14, 0.09 ), ( 0.11, 0.24, 0.16 ), ( 0.42, 0.96, 0.62 ), ( 0.74, 1.00, 0.80 ), ( 1.00, 0.56, 0.54 ), ( 0.86, 0.74, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "FROST HUNTER", "PRECISE RIFLE CORE", make_tag_array( "an94", "m27", "scar", "type95", "fal", "mtar" ), make_tag_array( "knife", "sickle", "", "", "", "" ), ( 0.06, 0.12, 0.18 ), ( 0.10, 0.20, 0.31 ), ( 0.54, 0.88, 1.00 ), ( 0.78, 0.95, 1.00 ), ( 1.00, 0.60, 0.55 ), ( 0.86, 0.76, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "PHANTOM OPERATIVE", "STEALTH SIDEARM CELL", make_tag_array( "b23r", "kap40", "mp7", "chicom", "skorpion", "smg" ), make_tag_array( "knife", "tazer", "", "", "", "" ), ( 0.09, 0.08, 0.14 ), ( 0.16, 0.14, 0.24 ), ( 0.74, 0.58, 1.00 ), ( 0.82, 0.90, 1.00 ), ( 1.00, 0.54, 0.58 ), ( 0.90, 0.78, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "BLOOD KNIGHT", "RIFLE + BLADE DUELIST", make_tag_array( "galil", "ak", "an94", "scar", "fal", "m8a1" ), make_tag_array( "bowie", "sickle", "knife", "shovel", "", "" ), ( 0.15, 0.07, 0.10 ), ( 0.26, 0.11, 0.17 ), ( 1.00, 0.36, 0.52 ), ( 1.00, 0.82, 0.86 ), ( 1.00, 0.56, 0.56 ), ( 0.90, 0.72, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "SCRAP GUNNER", "JURY-RIGGED FIREPOWER", make_tag_array( "ballistic", "crossbow", "python", "judge", "m1911", "mp5" ), make_tag_array( "knife", "bowie", "", "", "", "" ), ( 0.11, 0.10, 0.08 ), ( 0.20, 0.18, 0.13 ), ( 0.96, 0.82, 0.40 ), ( 0.95, 0.90, 0.72 ), ( 1.00, 0.62, 0.50 ), ( 0.88, 0.78, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "TEMPEST CALLER", "LIGHTNING PROTOCOL", make_tag_array( "storm", "thunder", "staff_lightning", "ray", "mark2", "paralyzer" ), make_tag_array( "galva", "tazer", "knife", "", "", "" ), ( 0.05, 0.11, 0.20 ), ( 0.10, 0.21, 0.33 ), ( 0.35, 0.86, 1.00 ), ( 0.66, 0.93, 1.00 ), ( 1.00, 0.58, 0.54 ), ( 0.84, 0.72, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "TOMB RAIDER", "RELIC EXCAVATION KIT", make_tag_array( "sniper", "svu", "fal", "shovel", "sickle", "knife" ), make_tag_array( "shovel", "sickle", "knife", "", "", "" ), ( 0.13, 0.10, 0.07 ), ( 0.22, 0.17, 0.11 ), ( 0.95, 0.78, 0.42 ), ( 0.97, 0.90, 0.72 ), ( 1.00, 0.60, 0.52 ), ( 0.88, 0.76, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "RIOT SURGEON", "SIDEARM CRITICAL CARE", make_tag_array( "pistol", "b23r", "kap40", "executioner", "judge", "five" ), make_tag_array( "knife", "bowie", "", "", "", "" ), ( 0.08, 0.13, 0.14 ), ( 0.13, 0.22, 0.23 ), ( 0.46, 0.95, 0.92 ), ( 0.72, 0.96, 0.95 ), ( 1.00, 0.58, 0.56 ), ( 0.86, 0.74, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "WASTELAND NOMAD", "SURVIVAL MIXED KIT", make_tag_array( "m1911", "mp5", "ak74u", "870", "galil", "remington" ), make_tag_array( "knife", "sickle", "", "", "", "" ), ( 0.10, 0.10, 0.11 ), ( 0.18, 0.18, 0.20 ), ( 0.86, 0.88, 0.94 ), ( 0.82, 0.92, 1.00 ), ( 1.00, 0.60, 0.56 ), ( 0.86, 0.76, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "BOX ADDICT", "MYSTERY CHEST FANATIC", make_tag_array( "ray", "mark2", "blundergat", "paralyzer", "sliquifier", "jetgun" ), make_tag_array( "knife", "galva", "tazer", "", "", "" ), ( 0.11, 0.07, 0.16 ), ( 0.20, 0.12, 0.27 ), ( 0.92, 0.54, 1.00 ), ( 0.88, 0.84, 1.00 ), ( 1.00, 0.58, 0.58 ), ( 0.92, 0.78, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "CATABOMB", "BLAST AND BREACH", make_tag_array( "launcher", "war", "rpg", "m1216", "s12", "870" ), make_tag_array( "knife", "bowie", "", "", "", "" ), ( 0.16, 0.09, 0.05 ), ( 0.27, 0.14, 0.08 ), ( 1.00, 0.62, 0.24 ), ( 1.00, 0.86, 0.62 ), ( 1.00, 0.56, 0.50 ), ( 0.90, 0.78, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "NIGHT STALKER", "SMG-SNIPER HYBRID", make_tag_array( "msmc", "mp7", "dsr", "ballista", "svu", "skorpion" ), make_tag_array( "knife", "sickle", "", "", "", "" ), ( 0.07, 0.07, 0.12 ), ( 0.13, 0.13, 0.21 ), ( 0.70, 0.72, 1.00 ), ( 0.78, 0.90, 1.00 ), ( 1.00, 0.58, 0.58 ), ( 0.90, 0.78, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "ORACLE OF FIRE", "FLAME CODEX", make_tag_array( "staff_fire", "ray", "mtar", "galil", "fal", "an94" ), make_tag_array( "knife", "bowie", "", "", "", "" ), ( 0.16, 0.07, 0.06 ), ( 0.28, 0.11, 0.10 ), ( 1.00, 0.42, 0.30 ), ( 1.00, 0.78, 0.68 ), ( 1.00, 0.54, 0.52 ), ( 0.90, 0.76, 1.00 ) );
    catalog[catalog.size] = create_class_theme( "APEX PREDATOR", "HIGH THREAT COMBO", make_tag_array( "an94", "msmc", "ray", "mark2", "m1216", "dsr" ), make_tag_array( "galva", "bowie", "knife", "", "", "" ), ( 0.08, 0.12, 0.08 ), ( 0.14, 0.22, 0.14 ), ( 0.56, 1.00, 0.60 ), ( 0.80, 1.00, 0.84 ), ( 1.00, 0.58, 0.56 ), ( 0.88, 0.80, 1.00 ) );

    return catalog;
}

build_default_class_theme()
{
    return create_class_theme( "SURVIVOR", "BALANCED START", make_tag_array( "", "", "", "", "", "" ), make_tag_array( "knife", "", "", "", "", "" ), ( 0.09, 0.12, 0.20 ), ( 0.12, 0.20, 0.30 ), ( 0.25, 0.72, 1.00 ), ( 0.60, 0.90, 1.00 ), ( 1.00, 0.52, 0.52 ), ( 0.86, 0.64, 1.00 ) );
}

create_class_theme(name, subtitle, weapon_tags, melee_tags, bg_color, header_color, accent_color, weapons_color, melee_color, perks_color)
{
    class_theme = spawnstruct();
    class_theme.name = name;
    class_theme.subtitle = subtitle;
    class_theme.weapon_tags = weapon_tags;
    class_theme.melee_tags = melee_tags;
    class_theme.bg_color = bg_color;
    class_theme.header_color = header_color;
    class_theme.accent_color = accent_color;
    class_theme.weapons_color = weapons_color;
    class_theme.melee_color = melee_color;
    class_theme.perks_color = perks_color;
    return class_theme;
}

make_tag_array(tag_0, tag_1, tag_2, tag_3, tag_4, tag_5)
{
    tags = [];

    if ( isdefined( tag_0 ) && tag_0 != "" )
        tags[tags.size] = tag_0;

    if ( isdefined( tag_1 ) && tag_1 != "" )
        tags[tags.size] = tag_1;

    if ( isdefined( tag_2 ) && tag_2 != "" )
        tags[tags.size] = tag_2;

    if ( isdefined( tag_3 ) && tag_3 != "" )
        tags[tags.size] = tag_3;

    if ( isdefined( tag_4 ) && tag_4 != "" )
        tags[tags.size] = tag_4;

    if ( isdefined( tag_5 ) && tag_5 != "" )
        tags[tags.size] = tag_5;

    return tags;
}

pick_random_class_themes(catalog, count)
{
    picked = [];
    used_idx = [];

    if ( !isdefined( catalog ) || catalog.size == 0 )
        return picked;

    attempts = 0;
    while ( picked.size < count && attempts < 1000 )
    {
        attempts++;
        idx = randomint( catalog.size );

        if ( array_contains( used_idx, idx ) )
            continue;

        used_idx[used_idx.size] = idx;
        picked[picked.size] = catalog[idx];
    }

    for ( i = 0; picked.size < count && i < catalog.size; i++ )
    {
        if ( array_contains( used_idx, i ) )
            continue;

        used_idx[used_idx.size] = i;
        picked[picked.size] = catalog[i];
    }

    return picked;
}

build_themed_weapons(weapon_pool, tags, count, avoid_weapons)
{
    result = [];
    themed_pool = filter_weapons_by_tags( weapon_pool, tags, avoid_weapons, result );
    picks = pick_random_unique( themed_pool, count );

    for ( i = 0; i < picks.size; i++ )
        result = add_unique( result, picks[i] );

    if ( result.size < count )
    {
        fallback_pool = filter_available_weapons( weapon_pool, avoid_weapons, result );
        fallback_picks = pick_random_unique( fallback_pool, count - result.size );

        for ( i = 0; i < fallback_picks.size; i++ )
            result = add_unique( result, fallback_picks[i] );
    }

    if ( result.size < count )
    {
        final_picks = pick_random_unique( weapon_pool, count - result.size );

        for ( i = 0; i < final_picks.size; i++ )
            result = add_unique( result, final_picks[i] );
    }

    return result;
}

build_themed_melee(melee_pool, tags)
{
    themed_pool = filter_weapons_by_tags( melee_pool, tags, undefined, undefined );
    picks = pick_random_unique( themed_pool, 1 );

    if ( picks.size > 0 )
        return picks[0];

    picks = pick_random_unique( melee_pool, 1 );

    if ( picks.size > 0 )
        return picks[0];

    return "knife_zm";
}

filter_weapons_by_tags(pool, tags, avoid_a, avoid_b)
{
    filtered = [];

    if ( !isdefined( pool ) || pool.size == 0 )
        return filtered;

    if ( !isdefined( tags ) || tags.size == 0 )
        return filtered;

    for ( i = 0; i < pool.size; i++ )
    {
        weapon = pool[i];

        if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
            continue;

        if ( isdefined( avoid_a ) && array_contains( avoid_a, weapon ) )
            continue;

        if ( isdefined( avoid_b ) && array_contains( avoid_b, weapon ) )
            continue;

        if ( weapon_matches_tags( weapon, tags ) )
            filtered = add_unique( filtered, weapon );
    }

    return filtered;
}

filter_available_weapons(pool, avoid_a, avoid_b)
{
    filtered = [];

    if ( !isdefined( pool ) || pool.size == 0 )
        return filtered;

    for ( i = 0; i < pool.size; i++ )
    {
        weapon = pool[i];

        if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
            continue;

        if ( isdefined( avoid_a ) && array_contains( avoid_a, weapon ) )
            continue;

        if ( isdefined( avoid_b ) && array_contains( avoid_b, weapon ) )
            continue;

        filtered = add_unique( filtered, weapon );
    }

    return filtered;
}

weapon_matches_tags(weapon_name, tags)
{
    if ( !isdefined( weapon_name ) || weapon_name == "" )
        return false;

    if ( !isdefined( tags ) || tags.size == 0 )
        return false;

    for ( i = 0; i < tags.size; i++ )
    {
        if ( !isdefined( tags[i] ) || tags[i] == "" )
            continue;

        if ( issubstr( weapon_name, tags[i] ) )
            return true;
    }

    return false;
}

build_weapon_pool()
{
    pool = [];

    if ( isdefined( level.zombie_weapons ) )
    {
        keys = getarraykeys( level.zombie_weapons );

        for ( i = 0; i < keys.size; i++ )
        {
            base_weapon = keys[i];
            pool = add_unique( pool, base_weapon );

            if ( isdefined( level.zombie_weapons[base_weapon] ) && isdefined( level.zombie_weapons[base_weapon].upgrade_name ) )
                pool = add_unique( pool, level.zombie_weapons[base_weapon].upgrade_name );
        }
    }

    if ( pool.size < 3 )
    {
        fallback = [];
        fallback[0] = "ray_gun_zm";
        fallback[1] = "raygun_mark2_zm";
        fallback[2] = "m1911_zm";
        fallback[3] = "ak74u_zm";
        fallback[4] = "mp5k_zm";

        for ( i = 0; i < fallback.size; i++ )
            pool = add_unique( pool, fallback[i] );
    }

    return pool;
}

build_melee_pool()
{
    pool = [];

    if ( isdefined( level._melee_weapons ) )
    {
        for ( i = 0; i < level._melee_weapons.size; i++ )
        {
            if ( isdefined( level._melee_weapons[i] ) && isdefined( level._melee_weapons[i].weapon_name ) )
                pool = add_unique( pool, level._melee_weapons[i].weapon_name );
        }
    }

    if ( isdefined( level.zombie_melee_weapon_list ) )
    {
        melee_keys = getarraykeys( level.zombie_melee_weapon_list );

        for ( i = 0; i < melee_keys.size; i++ )
            pool = add_unique( pool, melee_keys[i] );
    }

    if ( isdefined( level.zombie_weapons ) )
    {
        weapon_keys = getarraykeys( level.zombie_weapons );

        for ( i = 0; i < weapon_keys.size; i++ )
        {
            weapon_name = weapon_keys[i];

            if ( issubstr( weapon_name, "knife" ) || issubstr( weapon_name, "sickle" ) || issubstr( weapon_name, "tazer" ) || issubstr( weapon_name, "galva" ) || issubstr( weapon_name, "melee" ) || issubstr( weapon_name, "shovel" ) || issubstr( weapon_name, "tomahawk" ) )
                pool = add_unique( pool, weapon_name );
        }
    }

    filtered = [];

    for ( i = 0; i < pool.size; i++ )
    {
        if ( !isdefined( pool[i] ) || pool[i] == "" || pool[i] == "none" || pool[i] == "zombie_fists_zm" )
            continue;

        filtered = add_unique( filtered, pool[i] );
    }

    if ( filtered.size == 0 )
    {
        filtered = add_unique( filtered, "knife_zm" );
        filtered = add_unique( filtered, "bowie_knife_zm" );
        filtered = add_unique( filtered, "sickle_knife_zm" );
        filtered = add_unique( filtered, "tazer_knuckles_zm" );
    }

    return filtered;
}

build_perk_pool()
{
    pool = [];

    // Standard BO2 Zombies perks toggled per map.
    if ( isdefined( level.zombiemode_using_juggernaut_perk ) && level.zombiemode_using_juggernaut_perk )
        pool = add_unique( pool, "specialty_armorvest" );

    if ( isdefined( level.zombiemode_using_revive_perk ) && level.zombiemode_using_revive_perk )
        pool = add_unique( pool, "specialty_quickrevive" );

    if ( isdefined( level.zombiemode_using_sleightofhand_perk ) && level.zombiemode_using_sleightofhand_perk )
        pool = add_unique( pool, "specialty_fastreload" );

    if ( isdefined( level.zombiemode_using_doubletap_perk ) && level.zombiemode_using_doubletap_perk )
        pool = add_unique( pool, "specialty_rof" );

    if ( isdefined( level.zombiemode_using_marathon_perk ) && level.zombiemode_using_marathon_perk )
        pool = add_unique( pool, "specialty_longersprint" );

    if ( isdefined( level.zombiemode_using_deadshot_perk ) && level.zombiemode_using_deadshot_perk )
        pool = add_unique( pool, "specialty_deadshot" );

    if ( isdefined( level.zombiemode_using_additionalprimaryweapon_perk ) && level.zombiemode_using_additionalprimaryweapon_perk )
        pool = add_unique( pool, "specialty_additionalprimaryweapon" );

    if ( isdefined( level.zombiemode_using_tombstone_perk ) && level.zombiemode_using_tombstone_perk )
        pool = add_unique( pool, "specialty_scavenger" );

    if ( isdefined( level.zombiemode_using_chugabud_perk ) && level.zombiemode_using_chugabud_perk )
        pool = add_unique( pool, "specialty_finalstand" );

    if ( isdefined( level.zombiemode_using_divetonuke_perk ) && level.zombiemode_using_divetonuke_perk )
        pool = add_unique( pool, "specialty_flakjacket" );

    if ( isdefined( level.zombiemode_using_electric_cherry_perk ) && level.zombiemode_using_electric_cherry_perk )
        pool = add_unique( pool, "specialty_grenadepulldeath" );

    // Custom map perks (ex: Buried Vulture Aid).
    if ( isdefined( level._custom_perks ) )
    {
        custom_keys = getarraykeys( level._custom_perks );

        for ( i = 0; i < custom_keys.size; i++ )
        {
            if ( custom_keys[i] == "specialty_weapupgrade" )
                continue;

            pool = add_unique( pool, custom_keys[i] );
        }
    }

    // Jug is always guaranteed for every generated loadout.
    pool = add_unique( pool, "specialty_armorvest" );

    return pool;
}

build_random_perk_set(perk_pool)
{
    perks = [];
    perks = add_unique( perks, "specialty_armorvest" );

    candidates = [];
    for ( i = 0; i < perk_pool.size; i++ )
    {
        if ( perk_pool[i] == "specialty_armorvest" )
            continue;

        candidates = add_unique( candidates, perk_pool[i] );
    }

    attempts = 0;
    while ( perks.size < 5 && candidates.size > 0 && attempts < 500 )
    {
        attempts++;
        pick = candidates[randomint( candidates.size )];
        perks = add_unique( perks, pick );
    }

    // Fallbacks so we still land on exactly 5 perks.
    fallback_perks = [];
    fallback_perks[0] = "specialty_quickrevive";
    fallback_perks[1] = "specialty_fastreload";
    fallback_perks[2] = "specialty_rof";
    fallback_perks[3] = "specialty_longersprint";
    fallback_perks[4] = "specialty_deadshot";
    fallback_perks[5] = "specialty_additionalprimaryweapon";
    fallback_perks[6] = "specialty_scavenger";
    fallback_perks[7] = "specialty_finalstand";
    fallback_perks[8] = "specialty_flakjacket";
    fallback_perks[9] = "specialty_grenadepulldeath";
    fallback_perks[10] = "specialty_nomotionsensor";

    attempts = 0;
    while ( perks.size < 5 && attempts < 500 )
    {
        attempts++;
        perks = add_unique( perks, fallback_perks[randomint( fallback_perks.size )] );
    }

    return perks;
}

pick_random_unique(pool, count)
{
    result = [];

    if ( !isdefined( pool ) || pool.size == 0 )
        return result;

    max_count = count;
    if ( pool.size < max_count )
        max_count = pool.size;

    attempts = 0;
    while ( result.size < max_count && attempts < 1000 )
    {
        attempts++;
        candidate = pool[randomint( pool.size )];
        result = add_unique( result, candidate );
    }

    return result;
}

show_loadout_picker(loadouts)
{
    // Enforce a single active picker thread per player; prevents stacked duplicate HUD layers.
    self notify( "mod_picker_end" );
    self endon( "mod_picker_end" );

    if ( !isdefined( loadouts ) || loadouts.size == 0 )
        return 0;

    if ( isdefined( self.mod_picker_open ) && self.mod_picker_open && isdefined( self.mod_picker_menu ) )
        self destroy_picker_hud( self.mod_picker_menu );

    if ( isdefined( self.mod_picker_menu ) )
        self destroy_picker_hud( self.mod_picker_menu );

    self.mod_picker_open = 1;
    selected = 0;
    menu = self create_picker_hud();
    self.mod_picker_menu = menu;
    self thread picker_disconnect_cleanup( menu );
    self update_picker_hud( menu, loadouts, selected );

    start_time = gettime();
    timeout_ms = 45000;

    for (;;)
    {
        if ( !isalive( self ) )
            break;

        if ( self attackbuttonpressed() )
        {
            selected++;

            if ( selected >= loadouts.size )
                selected = 0;

            self wait_attack_release();
            self update_picker_hud( menu, loadouts, selected );
            continue;
        }

        if ( self adsbuttonpressed() )
        {
            selected--;

            if ( selected < 0 )
                selected = loadouts.size - 1;

            self wait_ads_release();
            self update_picker_hud( menu, loadouts, selected );
            continue;
        }

        if ( self usebuttonpressed() )
        {
            self wait_use_release();
            break;
        }

        if ( gettime() - start_time > timeout_ms )
            break;

        wait 0.05;
    }

    self notify( "picker_cleanup_done" );
    self destroy_picker_hud( menu );
    self.mod_picker_menu = undefined;
    self.mod_picker_open = 0;
    return selected;
}

picker_disconnect_cleanup(menu)
{
    self endon( "picker_cleanup_done" );
    self waittill( "disconnect" );
    self destroy_picker_hud( menu );
}

create_picker_hud()
{
    menu = spawnstruct();
    menu.all_elems = [];
    txt_scale = get_picker_text_scale();
    subtitle_scale = txt_scale;
    help_scale = txt_scale;
    section_scale = txt_scale;

    if ( !isdefined( self.mod_picker_instance_counter ) )
        self.mod_picker_instance_counter = 0;

    self.mod_picker_instance_counter++;
    menu.instance_id = self.mod_picker_instance_counter;

    menu.border = self create_picker_shader_elem( undefined, "CENTER", "CENTER", 0, 0, 584, 452, ( 0.05, 0.07, 0.12 ), 0.96, 10 );
    menu.box = self create_picker_shader_elem( undefined, "CENTER", "CENTER", 0, 0, 572, 440, ( 0.09, 0.12, 0.20 ), 0.90, 11 );
    menu.header = self create_picker_shader_elem( menu.box, "TOP", "TOP", 0, 22, 548, 44, ( 0.12, 0.20, 0.30 ), 0.96, 12 );
    menu.accent_rail = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 0, 0, 10, 440, ( 0.25, 0.72, 1.00 ), 0.95, 12 );
    menu.rule_a = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 22, 78, 530, 2, ( 0.25, 0.72, 1.00 ), 0.50, 12 );
    menu.rule_b = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 22, 258, 530, 2, ( 0.25, 0.72, 1.00 ), 0.50, 12 );
    menu.rule_c = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 22, 334, 530, 2, ( 0.25, 0.72, 1.00 ), 0.50, 12 );

    menu.line_title = self create_picker_text_elem( menu.box, "TOP", "TOP", 0, 8, "objective", txt_scale + 0.20, ( 0.25, 0.72, 1 ), 13 );
    menu.line_subtitle = self create_picker_text_elem( menu.box, "TOP", "TOP", 0, 42, "small", subtitle_scale, ( 0.82, 0.82, 0.82 ), 13 );

    menu.section_weapons = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 84, "default", section_scale, ( 0.25, 0.72, 1.00 ), 13 );
    menu.line_weap_1a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 112, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_1b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 56, 136, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_2a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 162, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_2b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 56, 186, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_3a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 212, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_3b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 56, 236, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );

    menu.section_melee = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 264, "default", section_scale, ( 1.00, 0.52, 0.52 ), 13 );
    menu.line_melee_a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 292, "small", txt_scale, ( 1, 0.52, 0.52 ), 13 );
    menu.line_melee_b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 56, 316, "small", txt_scale, ( 1, 0.52, 0.52 ), 13 );

    menu.section_perks = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 340, "default", section_scale, ( 0.86, 0.64, 1.00 ), 13 );
    menu.line_perks_a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 368, "small", txt_scale, ( 0.86, 0.64, 1 ), 13 );
    menu.line_perks_b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 56, 392, "small", txt_scale, ( 0.86, 0.64, 1 ), 13 );

    menu.line_help = self create_picker_text_elem( menu.box, "BOTTOM", "BOTTOM", 0, -14, "small", help_scale, ( 0.82, 0.82, 0.82 ), 13 );

    menu.all_elems[menu.all_elems.size] = menu.border;
    menu.all_elems[menu.all_elems.size] = menu.box;
    menu.all_elems[menu.all_elems.size] = menu.accent_rail;
    menu.all_elems[menu.all_elems.size] = menu.rule_a;
    menu.all_elems[menu.all_elems.size] = menu.rule_b;
    menu.all_elems[menu.all_elems.size] = menu.rule_c;
    menu.all_elems[menu.all_elems.size] = menu.header;
    menu.all_elems[menu.all_elems.size] = menu.line_title;
    menu.all_elems[menu.all_elems.size] = menu.line_subtitle;
    menu.all_elems[menu.all_elems.size] = menu.section_weapons;
    menu.all_elems[menu.all_elems.size] = menu.line_weap_1a;
    menu.all_elems[menu.all_elems.size] = menu.line_weap_1b;
    menu.all_elems[menu.all_elems.size] = menu.line_weap_2a;
    menu.all_elems[menu.all_elems.size] = menu.line_weap_2b;
    menu.all_elems[menu.all_elems.size] = menu.line_weap_3a;
    menu.all_elems[menu.all_elems.size] = menu.line_weap_3b;
    menu.all_elems[menu.all_elems.size] = menu.section_melee;
    menu.all_elems[menu.all_elems.size] = menu.line_melee_a;
    menu.all_elems[menu.all_elems.size] = menu.line_melee_b;
    menu.all_elems[menu.all_elems.size] = menu.section_perks;
    menu.all_elems[menu.all_elems.size] = menu.line_perks_a;
    menu.all_elems[menu.all_elems.size] = menu.line_perks_b;
    menu.all_elems[menu.all_elems.size] = menu.line_help;

    if ( getdvarint( "mod_picker_debug" ) == 1 )
    {
        menu.dbg_probe_100 = self create_picker_text_elem( undefined, "TOPLEFT", "TOPLEFT", 10, 10, "default", 1.00, ( 1, 1, 0.2 ), 200 );
        menu.dbg_probe_150 = self create_picker_text_elem( undefined, "TOPLEFT", "TOPLEFT", 10, 34, "default", 1.50, ( 1, 0.7, 0.2 ), 200 );
        menu.dbg_probe_200 = self create_picker_text_elem( undefined, "TOPLEFT", "TOPLEFT", 10, 66, "default", 2.00, ( 1, 0.4, 0.2 ), 200 );

        menu.dbg_probe_100 settext( "DBG scale 1.00" );
        menu.dbg_probe_150 settext( "DBG scale 1.50" );
        menu.dbg_probe_200 settext( "DBG scale 2.00" );

        menu.all_elems[menu.all_elems.size] = menu.dbg_probe_100;
        menu.all_elems[menu.all_elems.size] = menu.dbg_probe_150;
        menu.all_elems[menu.all_elems.size] = menu.dbg_probe_200;
    }

    return menu;
}

get_picker_text_scale()
{
    scale = getdvarfloat( "mod_picker_text_scale" );

    // BO2 HUD fontscale behaves reliably at >=1.0 for custom HUD text.
    if ( !isdefined( scale ) || scale < 1.00 || scale > 1.60 )
        scale = 1.00;

    return scale;
}

create_picker_shader_elem(parent, point, relative, x, y, width, height, color, alpha, sort)
{
    shader = self maps\mp\gametypes_zm\_hud_util::createicon( "white", width, height );

    if ( isdefined( parent ) )
        shader setparent( parent );

    shader maps\mp\gametypes_zm\_hud_util::setpoint( point, relative, x, y );
    shader.color = color;
    shader.alpha = alpha;
    shader.sort = sort;
    shader.archived = 0;
    shader.hidewheninmenu = 0;
    shader.foreground = 0;
    return shader;
}

create_picker_text_elem(parent, point, relative, x, y, font, scale, color, sort)
{
    text = self maps\mp\gametypes_zm\_hud_util::createfontstring( font, scale );

    if ( isdefined( parent ) )
        text setparent( parent );

    text maps\mp\gametypes_zm\_hud_util::setpoint( point, relative, x, y );
    text.alpha = 1;
    text.color = color;
    text.sort = sort;
    text.archived = 0;
    text.hidewheninmenu = 0;
    text.foreground = 1;
    if ( !isdefined( text.height ) || text.height < 1 )
        text.height = 1;
    text settext( "" );
    return text;
}

update_picker_hud(menu, loadouts, selected)
{
    if ( !isdefined( menu ) || !isdefined( menu.box ) )
        return;

    if ( !isdefined( loadouts ) || loadouts.size == 0 )
        return;

    if ( selected < 0 || selected >= loadouts.size )
        selected = 0;

    loadout = loadouts[selected];
    class_theme = build_default_class_theme();

    if ( isdefined( loadout.class_theme ) )
        class_theme = loadout.class_theme;

    if ( !isdefined( loadout.weapons ) )
        loadout.weapons = [];

    if ( !isdefined( loadout.perks ) )
        loadout.perks = [];

    weapon_0 = get_weapon_slot_name( loadout.weapons, 0, 48 );
    weapon_1 = get_weapon_slot_name( loadout.weapons, 1, 48 );
    weapon_2 = get_weapon_slot_name( loadout.weapons, 2, 48 );

    weapon_lines_0 = build_slot_lines( "1.", weapon_0, 18, 22 );
    weapon_lines_1 = build_slot_lines( "2.", weapon_1, 18, 22 );
    weapon_lines_2 = build_slot_lines( "3.", weapon_2, 18, 22 );

    if ( isdefined( loadout.melee ) )
        melee_pair = split_two_lines( sanitize_weapon_name( loadout.melee ), 22, 24 );
    else
        melee_pair = split_two_lines( "-", 22, 24 );

    perk_lines = build_perk_lines( loadout.perks, 30 );

    menu.border.color = ( 0.04, 0.06, 0.10 );
    menu.box.color = class_theme.bg_color;
    menu.box.alpha = 0.90;
    menu.header.color = class_theme.header_color;
    menu.accent_rail.color = class_theme.accent_color;
    menu.rule_a.color = class_theme.accent_color;
    menu.rule_b.color = class_theme.accent_color;
    menu.rule_c.color = class_theme.accent_color;

    menu.line_title.color = class_theme.accent_color;
    menu.line_subtitle.color = ( 0.88, 0.88, 0.88 );
    menu.section_weapons.color = class_theme.accent_color;
    menu.section_melee.color = class_theme.accent_color;
    menu.section_perks.color = class_theme.accent_color;

    menu.line_weap_1a.color = class_theme.weapons_color;
    menu.line_weap_1b.color = class_theme.weapons_color;
    menu.line_weap_2a.color = class_theme.weapons_color;
    menu.line_weap_2b.color = class_theme.weapons_color;
    menu.line_weap_3a.color = class_theme.weapons_color;
    menu.line_weap_3b.color = class_theme.weapons_color;

    menu.line_melee_a.color = class_theme.melee_color;
    menu.line_melee_b.color = class_theme.melee_color;
    menu.line_perks_a.color = class_theme.perks_color;
    menu.line_perks_b.color = class_theme.perks_color;

    title_text = class_theme.name + "  (" + ( selected + 1 ) + "/" + loadouts.size + ")";

    if ( getdvarint( "mod_picker_debug" ) == 1 )
        title_text += " [UI#" + menu.instance_id + "]";

    menu.line_title settext( title_text );
    menu.line_subtitle settext( class_theme.subtitle );
    menu.section_weapons settext( "WEAPONS" );
    menu.section_melee settext( "MELEE" );
    menu.section_perks settext( "PERKS" );

    menu.line_weap_1a settext( weapon_lines_0[0] );
    menu.line_weap_1b settext( weapon_lines_0[1] );
    menu.line_weap_2a settext( weapon_lines_1[0] );
    menu.line_weap_2b settext( weapon_lines_1[1] );
    menu.line_weap_3a settext( weapon_lines_2[0] );
    menu.line_weap_3b settext( weapon_lines_2[1] );

    menu.line_melee_a settext( melee_pair[0] );
    menu.line_melee_b settext( melee_pair[1] );

    menu.line_perks_a settext( perk_lines[0] );
    menu.line_perks_b settext( perk_lines[1] );

    help_text = "ADS: prev  ATTACK: next  USE: select";

    if ( getdvarint( "mod_picker_debug" ) == 1 )
        help_text += "  S=" + get_picker_text_scale();

    menu.line_help settext( help_text );
}

get_weapon_slot_name(weapons, slot_index, max_chars)
{
    if ( !isdefined( weapons ) || slot_index < 0 || slot_index >= weapons.size )
        return "-";

    return fit_label( sanitize_weapon_name( weapons[slot_index] ), max_chars );
}

build_slot_lines(slot_label, text, first_max_chars, second_max_chars)
{
    lines = [];
    lines[0] = slot_label + " -";
    lines[1] = "";

    wrapped = split_two_lines( text, first_max_chars, second_max_chars );
    lines[0] = slot_label + " " + wrapped[0];

    if ( wrapped[1] != "" )
        lines[1] = "   " + wrapped[1];

    return lines;
}

split_two_lines(text, first_max_chars, second_max_chars)
{
    lines = [];
    lines[0] = "-";
    lines[1] = "";

    if ( !isdefined( text ) || text == "" )
        return lines;

    if ( text.size <= first_max_chars )
    {
        lines[0] = text;
        return lines;
    }

    split_index = find_wrap_index( text, first_max_chars );
    first_line = getsubstr( text, 0, split_index );
    second_line = getsubstr( text, split_index, text.size );

    while ( isdefined( second_line ) && second_line != "" && getsubstr( second_line, 0, 1 ) == " " )
        second_line = getsubstr( second_line, 1, second_line.size );

    lines[0] = fit_label( first_line, first_max_chars );
    lines[1] = fit_label( second_line, second_max_chars );
    return lines;
}

find_wrap_index(text, max_chars)
{
    if ( !isdefined( text ) || text == "" )
        return 0;

    if ( text.size <= max_chars )
        return text.size;

    i = max_chars;
    while ( i > 1 )
    {
        if ( getsubstr( text, i - 1, i ) == " " )
            return i - 1;

        i--;
    }

    return max_chars;
}

build_weapon_summary(weapons)
{
    if ( !isdefined( weapons ) || weapons.size == 0 )
        return "none";

    text = "";

    for ( i = 0; i < weapons.size; i++ )
    {
        if ( i > 0 )
            text += " / ";

        text += sanitize_weapon_name( weapons[i] );
    }

    return text;
}

destroy_picker_hud(menu)
{
    if ( !isdefined( menu ) )
        return;

    if ( !isdefined( menu.all_elems ) )
        return;

    for ( i = 0; i < menu.all_elems.size; i++ )
    {
        if ( isdefined( menu.all_elems[i] ) )
            menu.all_elems[i] destroy();
    }
}

build_perk_lines(perks, max_chars)
{
    lines = [];
    lines[0] = "none";
    lines[1] = "none";

    if ( !isdefined( perks ) || perks.size == 0 )
        return lines;

    first = "";
    second = "";

    for ( i = 0; i < perks.size; i++ )
    {
        name = perk_to_short_name( perks[i] );

        if ( i < 3 )
        {
            if ( first != "" )
                first += ", ";

            first += name;
        }
        else if ( i < 5 )
        {
            if ( second != "" )
                second += ", ";

            second += name;
        }
    }

    if ( first != "" )
        lines[0] = fit_label( first, max_chars );

    if ( second != "" )
        lines[1] = fit_label( second, max_chars );

    return lines;
}

perk_to_short_name(perk)
{
    switch ( perk )
    {
        case "specialty_armorvest":
            return "Jug";
        case "specialty_quickrevive":
            return "QR";
        case "specialty_fastreload":
            return "Speed";
        case "specialty_rof":
            return "DTap";
        case "specialty_longersprint":
            return "Stamin";
        case "specialty_deadshot":
            return "Deadshot";
        case "specialty_additionalprimaryweapon":
            return "Mule";
        case "specialty_scavenger":
            return "Tomb";
        case "specialty_finalstand":
            return "WhosWho";
        case "specialty_flakjacket":
            return "PhD";
        case "specialty_grenadepulldeath":
            return "Cherry";
        case "specialty_nomotionsensor":
            return "Vulture";
        default:
            return perk_to_name( perk );
    }
}

sanitize_weapon_name(weapon)
{
    if ( !isdefined( weapon ) || weapon == "" )
        return "none";

    switch ( weapon )
    {
        case "knife_zm":
            return "Knife";
        case "bowie_knife_zm":
            return "Bowie Knife";
        case "sickle_knife_zm":
            return "Sickle";
        case "tazer_knuckles_zm":
            return "Galvaknuckles";
        case "ray_gun_zm":
            return "Ray Gun";
        case "ray_gun_upgraded_zm":
            return "Porter's X2 Ray Gun";
        case "raygun_mark2_zm":
            return "Ray Gun Mark II";
        case "raygun_mark2_upgraded_zm":
            return "Ray Gun Mark II (PAP)";
        default:
            break;
    }

    name = weapon;
    name = strip_suffix( name, "_zm" );
    name = strip_suffix( name, "_upgraded" );
    name = strip_suffix( name, "_upg" );

    tokens = strtok( name, "_" );
    pretty = "";

    for ( i = 0; i < tokens.size; i++ )
    {
        piece = tokens[i];

        if ( !isdefined( piece ) || piece == "" )
            continue;

        if ( piece == "mark2" )
            piece = "mk2";
        else if ( piece == "raygun" )
            piece = "ray gun";

        if ( pretty != "" )
            pretty += " ";

        pretty += piece;
    }

    if ( pretty == "" )
        return weapon;

    return pretty;
}

strip_suffix(text, suffix)
{
    if ( !isdefined( text ) || !isdefined( suffix ) )
        return text;

    if ( text.size < suffix.size )
        return text;

    if ( getsubstr( text, text.size - suffix.size, text.size ) == suffix )
        return getsubstr( text, 0, text.size - suffix.size );

    return text;
}

fit_label(text, max_chars)
{
    if ( !isdefined( text ) || text == "" )
        return "";

    if ( !isdefined( max_chars ) || max_chars < 4 )
        return text;

    if ( text.size <= max_chars )
        return text;

    clipped = getsubstr( text, 0, max_chars - 3 ) + "...";

    if ( getdvarint( "mod_picker_debug" ) == 1 )
        logprint( "mod_picker;truncate=\"" + text + "\";to=\"" + clipped + "\"\\n" );

    return clipped;
}

wait_attack_release()
{
    t = 0;
    while ( self attackbuttonpressed() && t < 40 )
    {
        wait 0.05;
        t++;
    }
}

wait_ads_release()
{
    t = 0;
    while ( self adsbuttonpressed() && t < 40 )
    {
        wait 0.05;
        t++;
    }
}

wait_use_release()
{
    t = 0;
    while ( self usebuttonpressed() && t < 40 )
    {
        wait 0.05;
        t++;
    }
}

apply_selected_loadout(loadout)
{
    if ( !isdefined( loadout ) )
        return;

    // Keep startup points from the previous setup.
    self.score = 10000;

    self takeAllWeapons();

    gave_any_weapon = false;

    for ( i = 0; i < loadout.weapons.size; i++ )
    {
        weapon = loadout.weapons[i];
        self giveWeapon(weapon);

        if ( self hasWeapon(weapon) )
        {
            self give_max_ammo(weapon);
            gave_any_weapon = true;
        }
    }

    if ( !gave_any_weapon )
    {
        self giveWeapon( "ray_gun_zm" );

        if ( self hasWeapon( "ray_gun_zm" ) )
        {
            self give_max_ammo( "ray_gun_zm" );
            gave_any_weapon = true;
        }
    }

    self give_selected_melee( loadout.melee );

    for ( i = 0; i < loadout.perks.size; i++ )
    {
        perk = loadout.perks[i];

        if ( !isdefined( perk ) || perk == "" )
            continue;

        if ( !self hasperk( perk ) )
            self maps\mp\zombies\_zm_perks::give_perk( perk, 0 );
    }

    for ( i = 0; i < loadout.weapons.size; i++ )
    {
        if ( self hasWeapon( loadout.weapons[i] ) )
        {
            self switchToWeapon( loadout.weapons[i] );
            break;
        }
    }
}

give_selected_melee(melee_weapon)
{
    if ( !isdefined( melee_weapon ) || melee_weapon == "" || melee_weapon == "none" )
        melee_weapon = "knife_zm";

    self maps\mp\zombies\_zm_weapons::weapon_give( melee_weapon, 0, 1, 1 );
}

format_weapon_list(weapons)
{
    if ( !isdefined( weapons ) || weapons.size == 0 )
        return "none";

    text = "";

    for ( i = 0; i < weapons.size; i++ )
    {
        if ( i > 0 )
            text += "^7 | ^5";

        text += weapons[i];
    }

    return text;
}

format_perk_list(perks)
{
    if ( !isdefined( perks ) || perks.size == 0 )
        return "none";

    text = "";

    for ( i = 0; i < perks.size; i++ )
    {
        if ( i > 0 )
            text += "^7, ^6";

        text += perk_to_name( perks[i] );
    }

    return text;
}

perk_to_name(perk)
{
    switch ( perk )
    {
        case "specialty_armorvest":
            return "Juggernog";
        case "specialty_quickrevive":
            return "Quick Revive";
        case "specialty_fastreload":
            return "Speed Cola";
        case "specialty_rof":
            return "Double Tap";
        case "specialty_longersprint":
            return "Stamin-Up";
        case "specialty_deadshot":
            return "Deadshot";
        case "specialty_additionalprimaryweapon":
            return "Mule Kick";
        case "specialty_scavenger":
            return "Tombstone";
        case "specialty_finalstand":
            return "Who's Who";
        case "specialty_flakjacket":
            return "PHD Flopper";
        case "specialty_grenadepulldeath":
            return "Electric Cherry";
        case "specialty_nomotionsensor":
            return "Vulture Aid";
        default:
            return perk;
    }
}

add_unique(target_array, value)
{
    if ( !isdefined( value ) || value == "" || value == "none" )
        return target_array;

    if ( !array_contains( target_array, value ) )
        target_array[target_array.size] = value;

    return target_array;
}

array_contains(target_array, value)
{
    if ( !isdefined( target_array ) )
        return false;

    for ( i = 0; i < target_array.size; i++ )
    {
        if ( target_array[i] == value )
            return true;
    }

    return false;
}

give_max_ammo(weapon)
{
    if ( !isdefined(weapon) || weapon == "" || weapon == "none" )
        return;

    self setWeaponAmmoClip(weapon, weaponClipSize(weapon));
    self setWeaponAmmoStock(weapon, weaponMaxAmmo(weapon));
}
