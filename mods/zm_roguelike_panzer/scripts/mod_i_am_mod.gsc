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
    rogue_log_event( "build", "id=2026-03-03-panzer-thundergun-v110-truth-alias-override" );

    // Defer thundergun precache until first .tg usage.
    // Startup precache can block map load when custom anim payloads are unstable.
    level.rogue_tg_precached = false;

    // Transit client commonly registers zombie_bus script-mover animtree first.
    // Register the same animtree on server before mech init to keep table order aligned.
    if ( rogue_is_transit_mapname() )
    {
        rogue_register_transit_bus_animtree_server();
        rogue_register_transit_bus_props_animtree_server();
        rogue_register_transit_automaton_animtree_server();
        rogue_register_transit_turbine_animtree_server();
        rogue_register_transit_clone_animtree_server();
        rogue_register_transit_cymbal_monkey_animtree_server();
    }

    // Disabled during crash triage: latest crashes are in _visionset_mgr::monitor.
    // Keep vanilla vsmgr registration path to avoid malformed custom overlay state.
    // rogue_register_burn_overlay_vsmgr();

    // _zm_ai_mechz registers clientfields during init(). That must happen in the
    // early startup window, not when player triggers .start later in the match.
    if ( rogue_is_zm_mapname_for_mech_init() )
        rogue_prepare_mech_fullport_runtime();

    // Normalize rampage bookmark globals early so _zm::watch_rampage_bookmark
    // never evaluates undefined values as bool.
    rogue_disable_rampage_bookmark();

    // Runtime safety net for intermittent "cannot cast undefined to bool"
    // crashes observed in core zombie threads (_zm_playerhealth/_zm_powerups).
    level thread rogue_bool_safety_sanitizer();
    level thread rogue_bootstrap();
    level thread on_player_connect();
}

rogue_bool_safety_sanitizer()
{
    if ( !isdefined( level.rogue_bool_sanitize_log_count ) )
        level.rogue_bool_sanitize_log_count = 0;

    if ( !isdefined( level.rogue_bool_sanitize_started ) )
    {
        level.rogue_bool_sanitize_started = 1;
        rogue_log_event( "bool_sanitize", "stage=start" );
    }

    for ( ;; )
    {
        wait 0.05;
        rogue_disable_rampage_bookmark();
        rogue_sanitize_vsmgr_state();
        rogue_sanitize_rampage_bookmark_state();
        rogue_install_powerup_player_valid_wrapper();
        players = get_players();

        for ( i = 0; i < players.size; i++ )
        {
            p = players[i];
            changed = 0;

            if ( !isdefined( p.flag ) )
            {
                p.flag = [];
                changed = 1;
            }

            if ( !isdefined( p.flags_lock ) )
            {
                p.flags_lock = [];
                changed = 1;
            }

            if ( !isdefined( p.flag["player_has_red_flashing_overlay"] ) )
            {
                p.flag["player_has_red_flashing_overlay"] = 0;
                changed = 1;
            }

            if ( !isdefined( p.flag["player_is_invulnerable"] ) )
            {
                p.flag["player_is_invulnerable"] = 0;
                changed = 1;
            }

            if ( !isdefined( p.hurtagain ) )
            {
                p.hurtagain = 0;
                changed = 1;
            }

            if ( changed && level.rogue_bool_sanitize_log_count < 30 )
            {
                cur_wpn = "<undef>";
                if ( isdefined( p getcurrentweapon() ) )
                    cur_wpn = p getcurrentweapon();

                rogue_log_event( "bool_sanitize_player", "idx=" + i + ";wpn=" + cur_wpn + ";fixed=1" );
                level.rogue_bool_sanitize_log_count++;
            }
        }

        rogue_sanitize_powerup_hud_defs();
    }
}

rogue_disable_rampage_bookmark()
{
    // Keep a sane count (>=1) instead of 0 to avoid edge behavior in core loop.
    if ( !isdefined( level.rampage_bookmark_kill_times_count ) || level.rampage_bookmark_kill_times_count < 1 || level.rampage_bookmark_kill_times_count > 8 )
        level.rampage_bookmark_kill_times_count = 3;

    if ( !isdefined( level.rampage_bookmark_kill_times_msec ) || level.rampage_bookmark_kill_times_msec < 1 )
        level.rampage_bookmark_kill_times_msec = 6000;

    if ( !isdefined( level.rampage_bookmark_kill_times_delay ) || level.rampage_bookmark_kill_times_delay < 0 )
        level.rampage_bookmark_kill_times_delay = 6000;
}

rogue_sanitize_rampage_bookmark_state()
{
    count = 3;
    if ( isdefined( level.rampage_bookmark_kill_times_count ) && level.rampage_bookmark_kill_times_count > 0 )
        count = level.rampage_bookmark_kill_times_count;

    players = get_players();
    for ( i = 0; i < players.size; i++ )
    {
        p = players[i];
        changed = 0;

        if ( !isdefined( p.rampage_bookmark_kill_times ) || !isarray( p.rampage_bookmark_kill_times ) )
        {
            p.rampage_bookmark_kill_times = [];
            changed = 1;
        }

        if ( !isdefined( p.ignore_rampage_kill_times ) )
        {
            p.ignore_rampage_kill_times = 0;
            changed = 1;
        }

        for ( j = 0; j < count; j++ )
        {
            if ( !isdefined( p.rampage_bookmark_kill_times[j] ) )
            {
                p.rampage_bookmark_kill_times[j] = 0;
                changed = 1;
            }
        }

        if ( changed && level.rogue_bool_sanitize_log_count < 30 )
        {
            cur_wpn = "<undef>";
            if ( isdefined( p getcurrentweapon() ) )
                cur_wpn = p getcurrentweapon();

            rogue_log_event( "bool_sanitize_rampage", "idx=" + i + ";wpn=" + cur_wpn + ";count=" + count );
            level.rogue_bool_sanitize_log_count++;
        }
    }
}

rogue_sanitize_rampage_bookmark_player( p )
{
    if ( !isdefined( p ) )
        return;

    count = 3;
    if ( isdefined( level.rampage_bookmark_kill_times_count ) && level.rampage_bookmark_kill_times_count > 0 )
        count = level.rampage_bookmark_kill_times_count;

    if ( !isdefined( p.rampage_bookmark_kill_times ) || !isarray( p.rampage_bookmark_kill_times ) )
        p.rampage_bookmark_kill_times = [];

    if ( !isdefined( p.ignore_rampage_kill_times ) )
        p.ignore_rampage_kill_times = 0;

    for ( j = 0; j < count; j++ )
    {
        if ( !isdefined( p.rampage_bookmark_kill_times[j] ) )
            p.rampage_bookmark_kill_times[j] = 0;
    }
}

rogue_sanitize_vsmgr_state()
{
    if ( !isdefined( level.vsmgr ) )
        return;

    types = getarraykeys( level.vsmgr );
    players = get_players();

    for ( t = 0; t < types.size; t++ )
    {
        type = types[t];

        if ( !isdefined( level.vsmgr[type] ) )
            continue;

        if ( !isdefined( level.vsmgr[type].in_use ) )
            level.vsmgr[type].in_use = 0;

        if ( !isdefined( level.vsmgr[type].info ) )
            level.vsmgr[type].info = [];

        info_keys = getarraykeys( level.vsmgr[type].info );
        for ( ik = 0; ik < info_keys.size; ik++ )
        {
            info_key = info_keys[ik];

            if ( !isdefined( level.vsmgr[type].info[info_key].state ) )
                continue;

            st = level.vsmgr[type].info[info_key].state;

            if ( !isdefined( st.players ) )
                st.players = [];

            for ( p = 0; p < players.size; p++ )
            {
                entnum = players[p] getentitynumber();

                if ( !isdefined( st.players[entnum] ) )
                    st.players[entnum] = spawnstruct();

                if ( !isdefined( st.players[entnum].active ) )
                    st.players[entnum].active = 0;

                if ( !isdefined( st.players[entnum].lerp ) )
                    st.players[entnum].lerp = 0;

                if ( isdefined( st.ref_count_lerp_thread ) && st.ref_count_lerp_thread && !isdefined( st.players[entnum].ref_count ) )
                    st.players[entnum].ref_count = 0;
            }
        }
    }
}

rogue_install_powerup_player_valid_wrapper()
{
    if ( !isdefined( level.powerup_player_valid ) )
        return;

    if ( isdefined( level.rogue_powerup_player_valid_wrapped ) && level.rogue_powerup_player_valid_wrapped )
        return;

    level.rogue_orig_powerup_player_valid = level.powerup_player_valid;
    level.powerup_player_valid = ::rogue_powerup_player_valid_safe;
    level.rogue_powerup_player_valid_wrapped = 1;

    if ( !isdefined( level.rogue_bool_sanitize_log_count ) )
        level.rogue_bool_sanitize_log_count = 0;

    if ( level.rogue_bool_sanitize_log_count < 30 )
    {
        rogue_log_event( "bool_sanitize", "wrapped=powerup_player_valid" );
        level.rogue_bool_sanitize_log_count++;
    }
}

rogue_powerup_player_valid_safe( player )
{
    if ( !isdefined( level.rogue_orig_powerup_player_valid ) )
        return true;

    result = [[ level.rogue_orig_powerup_player_valid ]]( player );

    if ( !isdefined( result ) )
    {
        if ( !isdefined( level.rogue_bool_sanitize_log_count ) )
            level.rogue_bool_sanitize_log_count = 0;

        if ( level.rogue_bool_sanitize_log_count < 30 )
        {
            cur_wpn = "<undef>";
            if ( isdefined( player ) && isdefined( player getcurrentweapon() ) )
                cur_wpn = player getcurrentweapon();

            rogue_log_event( "bool_sanitize", "undef_ret=powerup_player_valid;wpn=" + cur_wpn );
            level.rogue_bool_sanitize_log_count++;
        }

        return true;
    }

    return result;
}

rogue_sanitize_powerup_hud_defs()
{
    if ( !isdefined( level.zombie_powerups ) )
        return;

    if ( !isdefined( level.zombie_vars ) )
        level.zombie_vars = [];

    if ( !isdefined( level.zombie_vars["rogue_safe_powerup_on"] ) )
        level.zombie_vars["rogue_safe_powerup_on"] = 0;

    if ( !isdefined( level.zombie_vars["rogue_safe_powerup_time"] ) )
        level.zombie_vars["rogue_safe_powerup_time"] = 0;

    keys = getarraykeys( level.zombie_powerups );
    for ( k = 0; k < keys.size; k++ )
    {
        key = keys[k];

        if ( !isdefined( level.zombie_powerups[key].client_field_name ) )
            continue;

        if ( !isdefined( level.zombie_powerups[key].solo ) )
            level.zombie_powerups[key].solo = 0;

        if ( !isdefined( level.zombie_powerups[key].time_name ) || !isdefined( level.zombie_powerups[key].on_name ) )
        {
            level.zombie_powerups[key].time_name = "rogue_safe_powerup_time";
            level.zombie_powerups[key].on_name = "rogue_safe_powerup_on";

            if ( level.rogue_bool_sanitize_log_count < 30 )
            {
                rogue_log_event( "bool_sanitize_powerup", "key=" + key + ";fixed_missing_time_on=1" );
                level.rogue_bool_sanitize_log_count++;
            }
        }
    }
}

rogue_register_burn_overlay_vsmgr()
{
    if ( !isdefined( level.vsmgr_initializing ) || !level.vsmgr_initializing )
        return;

    if ( !isdefined( level.vsmgr ) || !isdefined( level.vsmgr["overlay"] ) || !isdefined( level.vsmgr["overlay"].info ) )
        return;

    if ( isdefined( level.vsmgr["overlay"].info["zm_transit_burn"] ) )
        return;

    if ( !isdefined( level.vsmgr_prio_overlay_zm_transit_burn ) )
        level.vsmgr_prio_overlay_zm_transit_burn = 20;

    if ( !isdefined( level.zm_transit_burn_max_duration ) )
        level.zm_transit_burn_max_duration = 2;

    maps\mp\_visionset_mgr::vsmgr_register_info(
        "overlay",
        "zm_transit_burn",
        1,
        level.vsmgr_prio_overlay_zm_transit_burn,
        15,
        1,
        maps\mp\_visionset_mgr::vsmgr_duration_lerp_thread_per_player,
        0
    );

    rogue_log_event( "vsmgr_register", "overlay=zm_transit_burn;version=1;prio=" + level.vsmgr_prio_overlay_zm_transit_burn );
}

rogue_is_zm_mapname_for_mech_init()
{
    map_name = tolower( getdvar( "mapname" ) );

    if ( !isdefined( map_name ) || map_name == "" )
        return false;

    if ( issubstr( map_name, "zm_" ) )
        return true;

    if ( issubstr( map_name, "so_z" ) )
        return true;

    return false;
}

rogue_is_transit_mapname()
{
    map_name = tolower( getdvar( "mapname" ) );

    if ( !isdefined( map_name ) || map_name == "" )
        return false;

    return issubstr( map_name, "transit" );
}

#using_animtree("zombie_bus");

rogue_register_transit_bus_animtree_server()
{
    scriptmodelsuseanimtree( #animtree );
}

#using_animtree("zombie_bus_props");

rogue_register_transit_bus_props_animtree_server()
{
    scriptmodelsuseanimtree( #animtree );
}

#using_animtree("zm_transit_automaton");

rogue_register_transit_automaton_animtree_server()
{
    scriptmodelsuseanimtree( #animtree );
}

#using_animtree("zombie_turbine");

rogue_register_transit_turbine_animtree_server()
{
    scriptmodelsuseanimtree( #animtree );
}

#using_animtree("zm_ally");

rogue_register_transit_clone_animtree_server()
{
    scriptmodelsuseanimtree( #animtree );
}

#using_animtree("zombie_cymbal_monkey");

rogue_register_transit_cymbal_monkey_animtree_server()
{
    scriptmodelsuseanimtree( #animtree );
}

on_player_connect()
{
    for (;;)
    {
        level waittill("connected", player);
        rogue_sanitize_rampage_bookmark_player( player );
        player thread rogue_rampage_bookmark_watchdog();
        player thread rogue_player_command_listener();
        player thread rogue_send_join_chat_hint();
        player thread on_player_spawn();
    }
}

rogue_rampage_bookmark_watchdog()
{
    self endon("disconnect");

    for ( ;; )
    {
        wait 0.01;
        rogue_sanitize_rampage_bookmark_player( self );
    }
}

rogue_send_join_chat_hint()
{
    self endon("disconnect");

    if ( isdefined( self.rogue_join_hint_sent ) && self.rogue_join_hint_sent )
        return;

    wait 1.0;

    if ( !is_zombies_map() )
        return;

    self.rogue_join_hint_sent = 1;
    self iprintln( "^1to start the gauntlet type start followed by your wager amount (^7example: /start 1000^1)" );
}

on_player_spawn()
{
    self endon("disconnect");

    for (;;)
    {
        self waittill("spawned_player");
        wait 0.8;
        rogue_sanitize_rampage_bookmark_player( self );

        if ( !is_zombies_map() )
            continue;

        if ( !isdefined( self.rogue_vm_watcher_started ) )
        {
            self.rogue_vm_watcher_started = 1;
            self thread rogue_thundergun_viewmodel_swap_watcher();
        }

        if ( !isdefined( self.mod_loadout_options ) || self.mod_loadout_options.size < 3 )
            self.mod_loadout_options = generate_loadout_options();

        if ( !isdefined( self.mod_selected_loadout ) )
            self.mod_selected_loadout = self show_loadout_picker( self.mod_loadout_options );

        if ( !isdefined( self.mod_selected_loadout ) )
            self.mod_selected_loadout = 0;

        if ( self.mod_selected_loadout < 0 || self.mod_selected_loadout >= self.mod_loadout_options.size )
            self.mod_selected_loadout = 0;

        self apply_selected_loadout( self.mod_loadout_options[self.mod_selected_loadout] );
        self rogue_apply_persistent_boon_effects();

        if ( isdefined( level.rogue_bootstrapped ) && level.rogue_bootstrapped && ( !isdefined( level.rogue_started ) || !level.rogue_started ) )
            self thread rogue_send_join_chat_hint();
    }
}

rogue_thundergun_viewmodel_swap_watcher()
{
    self endon( "disconnect" );

    for ( ;; )
    {
        wait 0.05;

        if ( !is_zombies_map() )
            continue;

        // Only swap after TG assets are precached (triggered by .tg).
        if ( !isdefined( level.rogue_tg_precached ) || !level.rogue_tg_precached )
            continue;

        // Gate the risky viewmodel swap behind a dvar (default off).
        // Use `set rogue_tg_viewhands_enable 1` to enable at runtime.
        if ( 0 == getdvarint( "rogue_tg_viewhands_enable" ) )
        {
            // If we were previously set, restore and stay disabled.
            if ( isdefined( self.rogue_vm_tg_set ) && self.rogue_vm_tg_set )
            {
                if ( isdefined( self.rogue_vm_default ) && self.rogue_vm_default != "" && self.rogue_vm_default != "viewmodel_usa_no_model" )
                    self setviewmodel( self.rogue_vm_default );

                self.rogue_vm_tg_set = 0;
                rogue_log_event( "tg_viewmodel", "stage=restore_disabled;vm=" + rogue_safe_str( self.rogue_vm_default ) + ";cur=" + self getcurrentweapon() );
            }

            continue;
        }

        want = false;
        if ( isdefined( self.rogue_tg_proxy_enabled ) && self.rogue_tg_proxy_enabled &&
             isdefined( self.rogue_tg_proxy_carrier ) && self.rogue_tg_proxy_carrier != "" )
        {
            if ( self getcurrentweapon() == self.rogue_tg_proxy_carrier )
                want = true;
        }

        if ( want )
        {
            if ( !isdefined( self.rogue_vm_tg_set ) || !self.rogue_vm_tg_set )
            {
                // Don't lock in a bad default (no_model can be active before the loadout is applied).
                if ( !isdefined( self.rogue_vm_default ) || self.rogue_vm_default == "" || self.rogue_vm_default == "viewmodel_usa_no_model" || self.rogue_vm_default == "rogue_tg_viewhands" )
                    self.rogue_vm_default = self getviewmodel();

                precachemodel( "rogue_tg_viewhands" );
                self setviewmodel( "rogue_tg_viewhands" );
                self.rogue_vm_tg_set = 1;
                rogue_log_event( "tg_viewmodel", "stage=set;vm=rogue_tg_viewhands;cur=" + self getcurrentweapon() );
            }
        }
        else
        {
            if ( isdefined( self.rogue_vm_tg_set ) && self.rogue_vm_tg_set )
            {
                if ( isdefined( self.rogue_vm_default ) && self.rogue_vm_default != "" && self.rogue_vm_default != "viewmodel_usa_no_model" )
                    self setviewmodel( self.rogue_vm_default );

                self.rogue_vm_tg_set = 0;
                rogue_log_event( "tg_viewmodel", "stage=restore;vm=" + self.rogue_vm_default + ";cur=" + self getcurrentweapon() );
            }
        }
    }
}

is_zombies_map()
{
    if ( isdefined( level.zombiemode ) && level.zombiemode )
        return true;

    return false;
}

rogue_perk_can_be_given(perk)
{
    if ( !isdefined( perk ) || perk == "" )
        return false;

    if ( perk == "specialty_additionalprimaryweapon" )
    {
        if ( isdefined( level.zombiemode_using_additionalprimaryweapon_perk ) && level.zombiemode_using_additionalprimaryweapon_perk )
            return true;

        return false;
    }

    return true;
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

        if ( is_invalid_loadout_weapon_name( weapon ) )
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

        if ( is_invalid_loadout_weapon_name( weapon ) )
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
            if ( !is_invalid_loadout_weapon_name( base_weapon ) )
                pool = add_unique( pool, base_weapon );

            if ( isdefined( level.zombie_weapons[base_weapon] ) && isdefined( level.zombie_weapons[base_weapon].upgrade_name ) )
            {
                upg = level.zombie_weapons[base_weapon].upgrade_name;

                if ( !is_invalid_loadout_weapon_name( upg ) )
                    pool = add_unique( pool, upg );
            }
        }
    }

    if ( pool.size < 3 )
    {
        fallback = [];
        fallback[0] = "ray_gun_zm";
        fallback[1] = "raygun_mark2_zm";
        fallback[2] = "thundergun_zm";
        fallback[3] = "thundergun_upgraded_zm";
        fallback[4] = "m1911_zm";
        fallback[5] = "ak74u_zm";
        fallback[6] = "mp5k_zm";
        fallback[7] = "m16a1_zm";

        for ( i = 0; i < fallback.size; i++ )
        {
            if ( !is_invalid_loadout_weapon_name( fallback[i] ) )
                pool = add_unique( pool, fallback[i] );
        }
    }

    return pool;
}

is_invalid_loadout_weapon_name(weapon_name)
{
    if ( !isdefined( weapon_name ) || weapon_name == "" || weapon_name == "none" )
        return true;

    w = tolower( weapon_name );

    if ( issubstr( w, "knife" ) || issubstr( w, "melee" ) || issubstr( w, "fists" ) )
        return true;

    if ( issubstr( w, "grenade" ) || issubstr( w, "claymore" ) || issubstr( w, "mine" ) || issubstr( w, "monkey" ) || issubstr( w, "tactical" ) )
        return true;

    if ( issubstr( w, "equip" ) || issubstr( w, "buildable" ) || issubstr( w, "specialty_" ) || issubstr( w, "no_melee" ) )
        return true;

    if ( w == "zombie_fists_zm" )
        return true;

    if ( is_melee_candidate_supported( weapon_name ) )
        return true;

    return false;
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

    filtered = [];

    for ( i = 0; i < pool.size; i++ )
    {
        if ( !isdefined( pool[i] ) || pool[i] == "" || pool[i] == "none" || pool[i] == "zombie_fists_zm" )
            continue;

        // Filter out ballistic/placeholder entries that fail on several survival maps.
        if ( issubstr( pool[i], "ballistic" ) || issubstr( pool[i], "no_melee" ) )
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
    fallback_perks = add_unique( fallback_perks, "specialty_quickrevive" );
    fallback_perks = add_unique( fallback_perks, "specialty_fastreload" );
    fallback_perks = add_unique( fallback_perks, "specialty_rof" );
    fallback_perks = add_unique( fallback_perks, "specialty_longersprint" );
    fallback_perks = add_unique( fallback_perks, "specialty_deadshot" );

    if ( rogue_perk_can_be_given( "specialty_additionalprimaryweapon" ) )
        fallback_perks = add_unique( fallback_perks, "specialty_additionalprimaryweapon" );

    fallback_perks = add_unique( fallback_perks, "specialty_scavenger" );
    fallback_perks = add_unique( fallback_perks, "specialty_finalstand" );
    fallback_perks = add_unique( fallback_perks, "specialty_flakjacket" );
    fallback_perks = add_unique( fallback_perks, "specialty_grenadepulldeath" );
    fallback_perks = add_unique( fallback_perks, "specialty_nomotionsensor" );

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
    self thread animate_picker_hud( menu );
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
    section_scale = txt_scale * 1.00;

    if ( !isdefined( self.mod_picker_instance_counter ) )
        self.mod_picker_instance_counter = 0;

    self.mod_picker_instance_counter++;
    menu.instance_id = self.mod_picker_instance_counter;

    menu.border = self create_picker_shader_elem( undefined, "CENTER", "CENTER", 0, 0, 642, 470, ( 0.04, 0.05, 0.10 ), 0.98, 10 );
    menu.box = self create_picker_shader_elem( undefined, "CENTER", "CENTER", 0, 0, 626, 454, ( 0.09, 0.12, 0.20 ), 0.92, 11 );
    menu.header = self create_picker_shader_elem( menu.box, "TOP", "TOP", 0, 24, 594, 48, ( 0.12, 0.20, 0.30 ), 0.96, 12 );
    menu.footer_plate = self create_picker_shader_elem( menu.box, "BOTTOM", "BOTTOM", 0, -14, 594, 28, ( 0.10, 0.14, 0.22 ), 0.82, 12 );
    menu.accent_rail = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 0, 0, 12, 454, ( 0.25, 0.72, 1.00 ), 0.95, 12 );

    // Keep shader count low to avoid BO2 HUD element-limit dropouts.
    menu.theme_dot_0 = self create_picker_shader_elem( menu.box, "TOPRIGHT", "TOPRIGHT", -150, 26, 8, 8, ( 0.25, 0.72, 1.00 ), 0.70, 13 );
    menu.theme_dot_1 = self create_picker_shader_elem( menu.box, "TOPRIGHT", "TOPRIGHT", -134, 26, 8, 8, ( 0.25, 0.72, 1.00 ), 0.52, 13 );
    menu.theme_dot_2 = self create_picker_shader_elem( menu.box, "TOPRIGHT", "TOPRIGHT", -118, 26, 8, 8, ( 0.25, 0.72, 1.00 ), 0.70, 13 );
    menu.rule_a = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 92, 578, 2, ( 0.25, 0.72, 1.00 ), 0.52, 12 );
    menu.rule_b = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 274, 578, 2, ( 0.25, 0.72, 1.00 ), 0.50, 12 );
    menu.rule_c = self create_picker_shader_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 350, 578, 2, ( 0.25, 0.72, 1.00 ), 0.50, 12 );

    menu.line_title = self create_picker_text_elem( menu.box, "TOP", "TOP", 0, 8, "objective", txt_scale + 0.25, ( 0.25, 0.72, 1 ), 13 );
    menu.line_subtitle = self create_picker_text_elem( menu.box, "TOP", "TOP", 0, 44, "small", subtitle_scale, ( 0.90, 0.90, 0.90 ), 13 );

    menu.section_weapons = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 28, 98, "small", section_scale, ( 0.25, 0.72, 1.00 ), 13 );
    menu.line_weap_1a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 126, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_1b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 48, 150, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_2a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 176, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_2b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 48, 200, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_3a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 226, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );
    menu.line_weap_3b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 48, 250, "small", txt_scale, ( 0.60, 0.90, 1 ), 13 );

    menu.section_melee = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 28, 282, "small", section_scale, ( 1.00, 0.52, 0.52 ), 13 );
    menu.line_melee_a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 310, "small", txt_scale, ( 1, 0.52, 0.52 ), 13 );
    menu.line_melee_b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 48, 334, "small", txt_scale, ( 1, 0.52, 0.52 ), 13 );

    menu.section_perks = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 28, 362, "small", section_scale, ( 0.90, 0.72, 1.00 ), 13 );
    menu.line_perks_a = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 24, 390, "small", txt_scale, ( 0.90, 0.72, 1 ), 13 );
    menu.line_perks_b = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 48, 414, "small", txt_scale, ( 0.90, 0.72, 1 ), 13 );

    menu.line_help = self create_picker_text_elem( menu.box, "BOTTOM", "BOTTOM", 0, -18, "small", help_scale, ( 0.88, 0.88, 0.88 ), 13 );

    menu.all_elems[menu.all_elems.size] = menu.border;
    menu.all_elems[menu.all_elems.size] = menu.box;
    menu.all_elems[menu.all_elems.size] = menu.footer_plate;
    menu.all_elems[menu.all_elems.size] = menu.theme_dot_0;
    menu.all_elems[menu.all_elems.size] = menu.theme_dot_1;
    menu.all_elems[menu.all_elems.size] = menu.theme_dot_2;
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

animate_picker_hud(menu)
{
    self endon( "picker_cleanup_done" );
    self endon( "disconnect" );

    if ( !isdefined( menu ) || !isdefined( menu.theme_dot_0 ) )
        return;

    pulse = 0;
    for (;;)
    {
        if ( pulse % 3 == 0 )
        {
            menu.theme_dot_0 fadeovertime( 0.25 );
            menu.theme_dot_0.alpha = 0.90;
            menu.theme_dot_1 fadeovertime( 0.25 );
            menu.theme_dot_1.alpha = 0.45;
            menu.theme_dot_2 fadeovertime( 0.25 );
            menu.theme_dot_2.alpha = 0.45;
            menu.header fadeovertime( 0.25 );
            menu.header.alpha = 0.96;
        }
        else if ( pulse % 3 == 1 )
        {
            menu.theme_dot_0 fadeovertime( 0.25 );
            menu.theme_dot_0.alpha = 0.45;
            menu.theme_dot_1 fadeovertime( 0.25 );
            menu.theme_dot_1.alpha = 0.90;
            menu.theme_dot_2 fadeovertime( 0.25 );
            menu.theme_dot_2.alpha = 0.45;
            menu.header fadeovertime( 0.25 );
            menu.header.alpha = 0.90;
        }
        else
        {
            menu.theme_dot_0 fadeovertime( 0.25 );
            menu.theme_dot_0.alpha = 0.45;
            menu.theme_dot_1 fadeovertime( 0.25 );
            menu.theme_dot_1.alpha = 0.45;
            menu.theme_dot_2 fadeovertime( 0.25 );
            menu.theme_dot_2.alpha = 0.90;
            menu.header fadeovertime( 0.25 );
            menu.header.alpha = 0.93;
        }

        pulse++;
        wait 0.30;
    }
}

get_picker_text_scale()
{
    scale = getdvarfloat( "mod_picker_text_scale" );

    // BO2 HUD fontscale behaves reliably at >=1.0 for this picker path.
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
    loadout = normalize_loadout( loadout );
    loadouts[selected] = loadout;
    class_theme = build_default_class_theme();

    if ( isdefined( loadout.class_theme ) )
        class_theme = loadout.class_theme;

    class_theme.accent_color = ensure_ui_color_visible( class_theme.accent_color, 0.44 );
    class_theme.weapons_color = ensure_ui_color_visible( class_theme.weapons_color, 0.52 );
    class_theme.melee_color = ensure_ui_color_visible( class_theme.melee_color, 0.52 );
    class_theme.perks_color = ensure_ui_color_visible( class_theme.perks_color, 0.56 );

    weapon_0 = get_weapon_slot_name( loadout.weapons, 0, 48 );
    weapon_1 = get_weapon_slot_name( loadout.weapons, 1, 48 );
    weapon_2 = get_weapon_slot_name( loadout.weapons, 2, 48 );

    weapon_lines_0 = build_slot_lines( "1.", weapon_0, 14, 16 );
    weapon_lines_1 = build_slot_lines( "2.", weapon_1, 14, 16 );
    weapon_lines_2 = build_slot_lines( "3.", weapon_2, 14, 16 );

    if ( isdefined( loadout.melee ) )
        melee_pair = split_two_lines( sanitize_weapon_name( loadout.melee ), 16, 18 );
    else
        melee_pair = split_two_lines( "-", 16, 18 );

    perk_lines = build_perk_lines( loadout.perks, 20 );

    menu.border.color = ( 0.04, 0.06, 0.10 );
    menu.box.color = class_theme.bg_color;
    menu.box.alpha = 0.90;
    menu.header.color = class_theme.header_color;
    menu.footer_plate.color = class_theme.header_color;
    menu.accent_rail.color = class_theme.accent_color;
    menu.theme_dot_0.color = class_theme.accent_color;
    menu.theme_dot_1.color = class_theme.accent_color;
    menu.theme_dot_2.color = class_theme.accent_color;
    menu.rule_a.color = class_theme.accent_color;
    menu.rule_b.color = class_theme.accent_color;
    menu.rule_c.color = class_theme.accent_color;

    menu.line_title.color = class_theme.accent_color;
    menu.line_subtitle.color = ( 0.88, 0.88, 0.88 );
    menu.section_weapons.color = class_theme.accent_color;
    menu.section_melee.color = class_theme.accent_color;
    menu.section_perks.color = class_theme.perks_color;

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
    menu.line_perks_a.alpha = 1;
    menu.line_perks_b.alpha = 1;

    title_text = class_theme.name + "  (" + ( selected + 1 ) + "/" + loadouts.size + ")";

    if ( getdvarint( "mod_picker_debug" ) == 1 )
        title_text += " [UI#" + menu.instance_id + "]";

    menu.line_title settext( title_text );
    menu.line_subtitle settext( fit_label( class_theme.subtitle, 42 ) );
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

ensure_ui_color_visible(color, min_luma)
{
    if ( !isdefined( color ) )
        return ( 0.85, 0.85, 0.85 );

    r = color[0];
    g = color[1];
    b = color[2];

    luma = r * 0.299 + g * 0.587 + b * 0.114;

    if ( luma >= min_luma )
        return ( r, g, b );

    boost = min_luma / ( luma + 0.001 );
    r = clamp_01( r * boost );
    g = clamp_01( g * boost );
    b = clamp_01( b * boost );
    return ( r, g, b );
}

clamp_01(v)
{
    if ( v < 0.0 )
        return 0.0;

    if ( v > 1.0 )
        return 1.0;

    return v;
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
    lines[0] = "-";
    lines[1] = "";

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

normalize_loadout(loadout)
{
    if ( !isdefined( loadout ) )
        loadout = spawnstruct();

    if ( !isdefined( loadout.weapons ) )
        loadout.weapons = [];

    if ( !isdefined( loadout.melee ) || loadout.melee == "" || loadout.melee == "none" )
        loadout.melee = "knife_zm";

    if ( !isdefined( loadout.perks ) )
        loadout.perks = [];

    weapon_pool = build_weapon_pool();
    guard = 0;
    while ( loadout.weapons.size < 3 && guard < 200 )
    {
        guard++;

        fallback_pick = pick_random_unique( weapon_pool, 1 );
        if ( fallback_pick.size < 1 )
            break;

        loadout.weapons = add_unique( loadout.weapons, fallback_pick[0] );
    }

    // Hard fallback in extremely restricted pools.
    if ( loadout.weapons.size < 1 )
        loadout.weapons = add_unique( loadout.weapons, "m1911_zm" );
    if ( loadout.weapons.size < 2 )
        loadout.weapons = add_unique( loadout.weapons, "ak74u_zm" );
    if ( loadout.weapons.size < 3 )
        loadout.weapons = add_unique( loadout.weapons, "mp5k_zm" );

    perk_seed = build_random_perk_set( build_perk_pool() );
    for ( i = 0; i < perk_seed.size && loadout.perks.size < 5; i++ )
        loadout.perks = add_unique( loadout.perks, perk_seed[i] );

    fallback_perks = [];
    fallback_perks = add_unique( fallback_perks, "specialty_armorvest" );
    fallback_perks = add_unique( fallback_perks, "specialty_quickrevive" );
    fallback_perks = add_unique( fallback_perks, "specialty_fastreload" );
    fallback_perks = add_unique( fallback_perks, "specialty_rof" );
    fallback_perks = add_unique( fallback_perks, "specialty_longersprint" );
    fallback_perks = add_unique( fallback_perks, "specialty_deadshot" );

    if ( rogue_perk_can_be_given( "specialty_additionalprimaryweapon" ) )
        fallback_perks = add_unique( fallback_perks, "specialty_additionalprimaryweapon" );

    fallback_perks = add_unique( fallback_perks, "specialty_scavenger" );
    fallback_perks = add_unique( fallback_perks, "specialty_finalstand" );
    fallback_perks = add_unique( fallback_perks, "specialty_flakjacket" );
    fallback_perks = add_unique( fallback_perks, "specialty_grenadepulldeath" );
    fallback_perks = add_unique( fallback_perks, "specialty_nomotionsensor" );

    attempts = 0;
    while ( loadout.perks.size < 5 && attempts < 200 )
    {
        attempts++;
        loadout.perks = add_unique( loadout.perks, fallback_perks[randomint( fallback_perks.size )] );
    }

    return loadout;
}

apply_selected_loadout(loadout)
{
    if ( !isdefined( loadout ) )
        return;

    loadout = normalize_loadout( loadout );

    if ( !isdefined( self.mod_start_points_given ) || !self.mod_start_points_given )
    {
        self.score = 10000;
        self.mod_start_points_given = 1;
    }

    self takeAllWeapons();

    if ( !isdefined( loadout.weapons ) )
        loadout.weapons = [];

    if ( loadout.weapons.size >= 3 && rogue_perk_can_be_given( "specialty_additionalprimaryweapon" ) && !self hasperk( "specialty_additionalprimaryweapon" ) )
        self maps\mp\zombies\_zm_perks::give_perk( "specialty_additionalprimaryweapon", 0 );

    given_weapons = [];

    for ( i = 0; i < loadout.weapons.size; i++ )
    {
        weapon = loadout.weapons[i];

        if ( self try_give_loadout_weapon( weapon ) )
            given_weapons = add_unique( given_weapons, weapon );
    }

    if ( given_weapons.size < 1 )
    {
        fallback_weapons = [];
        fallback_weapons[0] = "ray_gun_zm";
        fallback_weapons[1] = "m1911_zm";
        fallback_weapons[2] = "ak74u_zm";
        fallback_weapons[3] = "mp5k_zm";

        for ( i = 0; i < fallback_weapons.size && given_weapons.size < 2; i++ )
        {
            if ( self try_give_loadout_weapon( fallback_weapons[i] ) )
                given_weapons = add_unique( given_weapons, fallback_weapons[i] );
        }
    }

    self give_selected_melee( loadout.melee );

    for ( i = 0; i < loadout.perks.size; i++ )
    {
        perk = loadout.perks[i];

        if ( !isdefined( perk ) || perk == "" )
            continue;

        if ( !rogue_perk_can_be_given( perk ) )
            continue;

        if ( !self hasperk( perk ) )
            self maps\mp\zombies\_zm_perks::give_perk( perk, 0 );
    }

    for ( i = 0; i < given_weapons.size; i++ )
    {
        if ( self hasWeapon( given_weapons[i] ) )
        {
            self switchToWeapon( given_weapons[i] );
            break;
        }
    }
}

try_give_loadout_weapon(weapon)
{
    if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
        return false;

    if ( is_invalid_loadout_weapon_name( weapon ) )
        return false;

    tg_probe = issubstr( weapon, "thundergun" ) || issubstr( weapon, "rogue_probe_wpn" );
    if ( tg_probe )
        rogue_tg_log_player_state( self, "loadout_enter", weapon );

    // Match stock zombie devgui semantics first.
    is_upgraded = is_weapon_upgraded( weapon );
    if ( tg_probe )
    {
        included = maps\mp\zombies\_zm_weapons::is_weapon_included( weapon );
        included_or_base = included;
        if ( isdefined( maps\mp\zombies\_zm_weapons::is_weapon_or_base_included ) )
            included_or_base = maps\mp\zombies\_zm_weapons::is_weapon_or_base_included( weapon );
        can_use = self player_can_use_content( weapon );
        clip = weaponclipsize( weapon );
        max_ammo = weaponmaxammo( weapon );
        rogue_log_event( "tg_loadout_meta", "wpn=" + weapon + ";upg=" + is_upgraded + ";included=" + included + ";included_or_base=" + included_or_base + ";can_use=" + can_use + ";clip=" + rogue_safe_str( clip ) + ";max=" + rogue_safe_str( max_ammo ) );
    }

    // Non-destructive paths first: do not drop existing weapons until we know grant works.
    // Upgraded gives often require PAP options in T6 zombies.
    if ( is_upgraded )
        self giveWeapon( weapon, 0, self maps\mp\zombies\_zm_weapons::get_pack_a_punch_weapon_options( weapon ) );
    else
        self giveWeapon( weapon );
    wait 0.05;

    if ( tg_probe )
    {
        rogue_log_event( "tg_loadout_step", "path=giveWeapon;wpn=" + weapon + ";upg=" + is_upgraded + ";has=" + ( self hasWeapon( weapon ) ) + ";cur=" + self getcurrentweapon() );
        rogue_tg_log_player_state( self, "after_giveWeapon", weapon );
    }

    if ( self hasWeapon( weapon ) )
    {
        self give_max_ammo( weapon );
        return true;
    }

    // Retry direct with explicit overload for builds that require it.
    self giveWeapon( weapon, 0 );
    wait 0.05;

    if ( tg_probe )
    {
        rogue_log_event( "tg_loadout_step", "path=giveWeapon0;wpn=" + weapon + ";upg=" + is_upgraded + ";has=" + ( self hasWeapon( weapon ) ) + ";cur=" + self getcurrentweapon() );
        rogue_tg_log_player_state( self, "after_giveWeapon0", weapon );
    }

    if ( self hasWeapon( weapon ) )
    {
        self give_max_ammo( weapon );
        return true;
    }

    // For thundergun probing, stop here to avoid destructive loadout helper behavior.
    if ( tg_probe )
    {
        rogue_log_event( "tg_loadout_step", "path=weapon_give_skipped;wpn=" + weapon + ";upg=" + is_upgraded + ";reason=non_destructive_probe" );
        return false;
    }

    // Legacy destructive fallbacks for non-thundergun loadout flows only.
    self maps\mp\zombies\_zm_weapons::weapon_give( weapon, is_upgraded, 1, 1 );
    wait 0.05;

    if ( self hasWeapon( weapon ) )
    {
        self give_max_ammo( weapon );
        return true;
    }

    self maps\mp\zombies\_zm_weapons::weapon_give( weapon, is_upgraded, 0 );
    wait 0.05;

    if ( self hasWeapon( weapon ) )
    {
        self give_max_ammo( weapon );
        return true;
    }

    return false;
}

try_give_weapon_direct_strict(weapon)
{
    if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
        return false;

    if ( is_invalid_loadout_weapon_name( weapon ) )
        return false;

    is_upgraded = is_weapon_upgraded( weapon );

    // Direct give first so unknown names do not get silently substituted by ZM helper paths.
    if ( is_upgraded )
        self giveWeapon( weapon, 0, self maps\mp\zombies\_zm_weapons::get_pack_a_punch_weapon_options( weapon ) );
    else
        self giveWeapon( weapon );
    wait 0.05;

    if ( self hasWeapon( weapon ) )
    {
        self give_max_ammo( weapon );
        return true;
    }

    // Retry direct with explicit overload for builds that require it.
    self giveWeapon( weapon, 0 );
    wait 0.05;

    if ( self hasWeapon( weapon ) )
    {
        self give_max_ammo( weapon );
        return true;
    }

    return false;
}

give_selected_melee(melee_weapon)
{
    candidates = [];

    if ( isdefined( melee_weapon ) && melee_weapon != "" && melee_weapon != "none" )
        candidates[candidates.size] = melee_weapon;

    if ( isdefined( level.zombie_melee_weapon_player_init ) && level.zombie_melee_weapon_player_init != "" )
        candidates = add_unique( candidates, level.zombie_melee_weapon_player_init );

    candidates = add_unique( candidates, "knife_zm" );
    candidates = add_unique( candidates, "bowie_knife_zm" );
    candidates = add_unique( candidates, "sickle_knife_zm" );
    candidates = add_unique( candidates, "tazer_knuckles_zm" );

    for ( i = 0; i < candidates.size; i++ )
    {
        candidate = candidates[i];

        if ( !is_melee_candidate_supported( candidate ) )
            continue;

        self maps\mp\zombies\_zm_weapons::weapon_give( candidate, 0, 1, 1 );
        wait 0.05;

        if ( isdefined( self.current_melee_weapon ) && self.current_melee_weapon == candidate )
            return;

        if ( self hasweapon( candidate ) )
            return;
    }
}

is_melee_candidate_supported(candidate)
{
    if ( !isdefined( candidate ) || candidate == "" || candidate == "none" )
        return false;

    if ( issubstr( candidate, "ballistic" ) || issubstr( candidate, "no_melee" ) )
        return false;

    if ( isdefined( level._melee_weapons ) )
    {
        for ( i = 0; i < level._melee_weapons.size; i++ )
        {
            if ( isdefined( level._melee_weapons[i] ) && isdefined( level._melee_weapons[i].weapon_name ) && level._melee_weapons[i].weapon_name == candidate )
                return true;
        }
    }

    if ( isdefined( level.zombie_melee_weapon_list ) )
    {
        keys = getarraykeys( level.zombie_melee_weapon_list );

        for ( i = 0; i < keys.size; i++ )
        {
            if ( keys[i] == candidate )
                return true;
        }
    }

    if ( candidate == "knife_zm" || candidate == "bowie_knife_zm" || candidate == "sickle_knife_zm" || candidate == "tazer_knuckles_zm" )
        return true;

    return false;
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

rogue_bootstrap()
{
    // On some loads this script starts before level.zombiemode is initialized.
    // Wait briefly so chat listeners are always registered on ZM maps.
    wait_frames = 0;
    while ( !is_zombies_map() && wait_frames < 400 )
    {
        wait 0.05;
        wait_frames++;
    }

    if ( !is_zombies_map() )
    {
        map_name = tolower( getdvar( "mapname" ) );

        if ( !isdefined( map_name ) || map_name.size < 3 )
            return;

        if ( getsubstr( map_name, 0, 3 ) != "zm_" && getsubstr( map_name, 0, 3 ) != "so_" )
            return;
    }

    if ( isdefined( level.rogue_bootstrapped ) && level.rogue_bootstrapped )
        return;

    level.rogue_bootstrapped = 1;
    level.rogue_started = 0;
    level.rogue_completed = 0;
    level.rogue_round_goal = 10;
    level.rogue_target_round = 1;
    level.rogue_entry_fee = 0;
    level.rogue_boon_in_progress = 0;
    level.rogue_last_round_started = undefined;
    level thread rogue_level_command_listener( "say" );
    level thread rogue_level_command_listener( "sayall" );
    level thread rogue_level_command_listener( "sayteam" );
    level thread rogue_round_end_monitor();
    level thread rogue_prepare_idle_state();
    if ( getdvarint( "rogue_town_debug_spawn" ) == 1 )
        level thread rogue_town_panzer_debug_spawn_once();
}

rogue_prepare_idle_state()
{
    while ( !isdefined( level.round_spawn_func ) )
        wait 0.1;

    if ( isdefined( level.round_start_custom_func ) && level.round_start_custom_func != ::rogue_round_start_custom )
        level.rogue_prev_round_start_custom = level.round_start_custom_func;

    level.round_start_custom_func = ::rogue_round_start_custom;
    rogue_pause_zombie_spawns();
    rogue_broadcast( "^3Rogue Gauntlet:^7 type ^2.start 1000^7 in chat to begin." );
}

rogue_pause_zombie_spawns()
{
    common_scripts\utility::flag_clear( "spawn_zombies" );
    level.rogue_spawns_paused = 1;
    if ( isdefined( level.mechz_left_to_spawn ) )
        level.mechz_left_to_spawn = 0;

    if ( isdefined( level.rogue_panzer_mode ) && level.rogue_panzer_mode )
    {
        if ( isdefined( level.rogue_wave_spawning ) && level.rogue_wave_spawning )
            return;

        rogue_kill_non_panzer_enemies();
        return;
    }

    enemies = maps\mp\zombies\_zm_utility::get_round_enemy_array();

    for ( i = 0; i < enemies.size; i++ )
    {
        if ( !isdefined( enemies[i] ) )
            continue;

        enemies[i] dodamage( enemies[i].health + 10000, enemies[i].origin );
    }
}

rogue_resume_zombie_spawns()
{
    common_scripts\utility::flag_set( "spawn_zombies" );
    level.rogue_spawns_paused = 0;
}

rogue_level_command_listener(event_name)
{
    for (;;)
    {
        level waittill( event_name, arg1, arg2, arg3, arg4 );

        player = rogue_find_player_arg( arg1, arg2, arg3, arg4 );
        rogue_try_handle_chat_arg( player, arg1, event_name );
        rogue_try_handle_chat_arg( player, arg2, event_name );
        rogue_try_handle_chat_arg( player, arg3, event_name );
        rogue_try_handle_chat_arg( player, arg4, event_name );
    }
}

rogue_find_player_arg(arg1, arg2, arg3, arg4)
{
    if ( isdefined( arg1 ) && isplayer( arg1 ) )
        return arg1;

    if ( isdefined( arg2 ) && isplayer( arg2 ) )
        return arg2;

    if ( isdefined( arg3 ) && isplayer( arg3 ) )
        return arg3;

    if ( isdefined( arg4 ) && isplayer( arg4 ) )
        return arg4;

    return undefined;
}

rogue_try_handle_chat_arg(player, arg, event_name)
{
    if ( !isdefined( arg ) || isplayer( arg ) )
        return;

    text = "" + arg;
    text = rogue_normalize_chat_text( text );

    if ( text == "" )
        return;

    if ( isdefined( player ) && isplayer( player ) && getdvarint( "rogue_chat_debug" ) == 1 )
        player iprintln( "^3chat seen [" + event_name + "]:^7 " + text );

    rogue_try_handle_chat_command( player, text );
}

rogue_normalize_chat_text(text)
{
    if ( !isdefined( text ) || text == "" )
        return "";

    t = tolower( text );

    while ( t != "" && getsubstr( t, 0, 1 ) == " " )
        t = getsubstr( t, 1, t.size );

    if ( t == "" )
        return "";

    // Some builds prepend a random/broken first character.
    if ( t[0] != "." && t[0] != "/" && t[0] != "s" )
        t = getsubstr( t, 1, t.size );

    return t;
}

rogue_player_command_listener()
{
    self endon( "disconnect" );
    self thread rogue_player_say_listener( "say" );
    self thread rogue_player_say_listener( "sayall" );
    self thread rogue_player_say_listener( "sayteam" );
    self thread rogue_player_custom_cmd_listener();
}

rogue_player_say_listener(event_name)
{
    self endon( "disconnect" );

    for (;;)
    {
        self waittill( event_name, arg1, arg2, arg3, arg4 );
        rogue_try_handle_chat_arg( self, arg1, event_name + "_self" );
        rogue_try_handle_chat_arg( self, arg2, event_name + "_self" );
        rogue_try_handle_chat_arg( self, arg3, event_name + "_self" );
        rogue_try_handle_chat_arg( self, arg4, event_name + "_self" );
    }
}

rogue_player_custom_cmd_listener()
{
    self endon( "disconnect" );

    for (;;)
    {
        self waittill( "custom_cmd", cmd, arg0, arg1, arg2 );

        text = "";

        if ( isdefined( cmd ) && !isplayer( cmd ) )
            text = "" + cmd;

        if ( isdefined( arg0 ) && !isplayer( arg0 ) )
            text += " " + arg0;

        if ( isdefined( arg1 ) && !isplayer( arg1 ) )
            text += " " + arg1;

        if ( isdefined( arg2 ) && !isplayer( arg2 ) )
            text += " " + arg2;

        rogue_try_handle_chat_command( self, text );
    }
}

rogue_try_handle_chat_command(source_player, raw_text)
{
    if ( !isdefined( raw_text ) || raw_text == "" )
        return;

    if ( isplayer( raw_text ) )
        return;

    text = "" + raw_text;

    if ( rogue_try_handle_utility_command( source_player, text ) )
        return;

    entry_fee = rogue_extract_start_entry( text );

    if ( entry_fee < 0 )
        return;

    if ( !isdefined( source_player ) || !isplayer( source_player ) )
    {
        players = getplayers();

        if ( isdefined( players ) && players.size == 1 && isdefined( players[0] ) )
            source_player = players[0];
        else
            return;
    }

    source_player iprintlnbold( "^2Rogue command detected:^7 start " + entry_fee );

    rogue_start_gauntlet( source_player, entry_fee );
}

rogue_try_handle_utility_command(source_player, raw_text)
{
    if ( !isdefined( source_player ) || !isplayer( source_player ) )
        return false;

    cmd_text = tolower( "" + raw_text );
    parts = strtok( cmd_text, " " );

    if ( !isdefined( parts ) || parts.size < 1 )
        return false;

    token = parts[0];
    if ( !isdefined( token ) || token == "" )
        return false;

    if ( token == ".tg" || token == "tg" || token == "/tg" || token == ".thundergun" || token == "thundergun" || token == "/thundergun" )
    {
        use_upgraded = false;
        no_switch = false;
        requested_non_truth_mode = false;

        for ( ai = 1; ai < parts.size; ai++ )
        {
            mode = parts[ai];
            if ( mode == "upg" || mode == "upgraded" || mode == "pap" )
                use_upgraded = true;
            else if ( mode == "raw" || mode == "proxy" || mode == "bo3" || mode == "custom" || mode == "base" )
                requested_non_truth_mode = true;
            else if ( mode == "noswitch" || mode == "safe" )
                no_switch = true;
        }

        if ( requested_non_truth_mode )
            rogue_log_event( "tg_step", "stage=truth_mode_locked;upg=" + use_upgraded + ";noswitch=" + no_switch );

        rogue_give_thundergun( source_player, use_upgraded, no_switch, false );
        return true;
    }

    if ( token == ".tp" || token == "tp" || token == "/tp" || token == ".3p" || token == "/3p" || token == ".thirdperson" || token == "thirdperson" || token == "/thirdperson" )
    {
        if ( !isdefined( source_player.rogue_thirdperson ) )
            source_player.rogue_thirdperson = false;

        source_player.rogue_thirdperson = !source_player.rogue_thirdperson;

        if ( source_player.rogue_thirdperson )
        {
            source_player setclientdvar( "cg_thirdPerson", 1 );
            source_player setclientdvar( "cg_thirdPersonRange", 120 );
            source_player iprintlnbold( "^2Third person: ON" );
        }
        else
        {
            source_player setclientdvar( "cg_thirdPerson", 0 );
            source_player iprintlnbold( "^1Third person: OFF" );
        }
        return true;
    }

    return false;
}

rogue_give_thundergun(player, use_upgraded, no_switch, force_raw)
{
    if ( !isdefined( player ) || !isplayer( player ) )
        return;

    run_mode = "truth";

    if ( !isalive( player ) )
    {
        player iprintlnbold( "^1You must be alive to use this command." );
        rogue_log_event( "tg_result", "mode=" + run_mode + ";ok=0;reason=not_alive;cur=" + player getcurrentweapon() );
        return;
    }

    rogue_log_event( "tg_step", "stage=enter_give;cur=" + player getcurrentweapon() );
    rogue_tg_log_player_state( player, "enter_give", "" );
    rogue_thundergun_ensure_vars();
    rogue_log_event( "tg_step", "stage=after_ensure_vars" );
    reg_ok = rogue_register_thundergun_with_zm_weapons();
    rogue_log_event( "tg_step", "stage=after_register_call;ok=" + reg_ok );
    rogue_log_event( "tg_step", "stage=registry;ok=" + reg_ok + ";has_stock=" + isdefined( level.zombie_weapons["thundergun_zm"] ) + ";has_stock_upg=" + isdefined( level.zombie_weapons["thundergun_upgraded_zm"] ) );
    rogue_precache_thundergun_items();

    truth_ok = rogue_try_give_thundergun_truth( player, use_upgraded, no_switch );
    truth_cur = player getcurrentweapon();
    if ( truth_ok )
    {
        rogue_log_event( "tg_give", "wpn=" + truth_cur + ";has=1;mode=truth;cur=" + truth_cur );
        rogue_log_event( "tg_result", "mode=truth;ok=1;wpn=" + truth_cur + ";cur=" + truth_cur );
        rogue_tg_log_player_state( player, "final_truth_ok", truth_cur );
        player iprintlnbold( "^2Thundergun truth weapon granted." );
        return;
    }

    fail_wpn = "thundergun_zm";
    if ( isdefined( level.rogue_tg_truth_weapon ) && level.rogue_tg_truth_weapon != "" )
        fail_wpn = level.rogue_tg_truth_weapon;
    rogue_log_event( "tg_give", "wpn=" + fail_wpn + ";has=0;mode=truth;cur=" + truth_cur );
    rogue_log_event( "tg_result", "mode=truth;ok=0;reason=alias_grant_failed;cur=" + truth_cur );
    rogue_tg_log_player_state( player, "final_truth_fail", fail_wpn );
    player iprintlnbold( "^1Thundergun truth weapon FAILED - alias grant blocked." );
}

rogue_try_give_thundergun_truth(player, use_upgraded, no_switch)
{
    if ( !isdefined( player ) || !isplayer( player ) )
        return false;

    base_truth = "thundergun_zm";
    upg_truth = "thundergun_upgraded_zm";
    if ( isdefined( level.rogue_tg_truth_weapon ) && level.rogue_tg_truth_weapon != "" )
        base_truth = level.rogue_tg_truth_weapon;
    if ( isdefined( level.rogue_tg_truth_weapon_upg ) && level.rogue_tg_truth_weapon_upg != "" )
        upg_truth = level.rogue_tg_truth_weapon_upg;

    candidates = [];
    candidates[0] = base_truth;
    if ( isdefined( use_upgraded ) && use_upgraded )
        candidates[candidates.size] = upg_truth;

    for ( ci = 0; ci < candidates.size; ci++ )
    {
        wpn = candidates[ci];
        inc = maps\mp\zombies\_zm_weapons::is_weapon_included( wpn );
        inc_or_base = inc;
        if ( isdefined( maps\mp\zombies\_zm_weapons::is_weapon_or_base_included ) )
            inc_or_base = maps\mp\zombies\_zm_weapons::is_weapon_or_base_included( wpn );
        can_use = player player_can_use_content( wpn );
        had_before = player hasweapon( wpn );
        clip = weaponclipsize( wpn );
        max_ammo = weaponmaxammo( wpn );
        rogue_log_event( "tg_truth_attempt", "wpn=" + wpn + ";idx=" + ci + ";upg_req=" + ( isdefined( use_upgraded ) && use_upgraded ) + ";inc=" + inc + ";inc_or_base=" + inc_or_base + ";can_use=" + can_use + ";had_before=" + had_before + ";clip=" + rogue_safe_str( clip ) + ";max=" + rogue_safe_str( max_ammo ) + ";cur=" + player getcurrentweapon() );

        direct_ok = player try_give_weapon_direct_strict( wpn );
        has_after_direct = player hasweapon( wpn );
        inv_count = player getweaponslist( 1 ).size;
        rogue_log_event( "tg_truth_result", "wpn=" + wpn + ";idx=" + ci + ";path=direct;ok=" + direct_ok + ";has_after=" + has_after_direct + ";inv_count=" + inv_count + ";cur=" + player getcurrentweapon() );

        loadout_ok = false;
        if ( !has_after_direct )
        {
            loadout_ok = player try_give_loadout_weapon( wpn );
            has_after = player hasweapon( wpn );
            inv_count = player getweaponslist( 1 ).size;
            rogue_log_event( "tg_truth_result", "wpn=" + wpn + ";idx=" + ci + ";path=loadout;ok=" + loadout_ok + ";has_after=" + has_after + ";inv_count=" + inv_count + ";cur=" + player getcurrentweapon() );
        }
        else
            has_after = true;

        if ( !has_after )
        {
            fail_reason = "grant_failed";
            clip_unreg = true;
            if ( isdefined( clip ) && isdefined( max_ammo ) )
                clip_unreg = ( clip <= 0 && max_ammo <= 0 );
            if ( clip_unreg )
                fail_reason = "weapondef_unregistered";
            else if ( !inc_or_base )
                fail_reason = "not_included";
            else if ( !can_use )
                fail_reason = "content_gate";
            rogue_log_event( "tg_truth_fail_reason", "wpn=" + wpn + ";idx=" + ci + ";reason=" + fail_reason + ";inc=" + inc + ";inc_or_base=" + inc_or_base + ";can_use=" + can_use + ";direct_ok=" + direct_ok + ";loadout_ok=" + loadout_ok + ";cur=" + player getcurrentweapon() );
            continue;
        }

        if ( wpn == "thundergun_zm" || wpn == "thundergun_upgraded_zm" )
        {
            player.rogue_tg_proxy_enabled = false;
            player.rogue_tg_proxy_carrier = "";
        }
        else
        {
            // Truth alias override path: use watcher proxy trigger on the carrier weapon.
            player.rogue_tg_proxy_enabled = true;
            player.rogue_tg_proxy_carrier = wpn;
            rogue_log_event( "tg_truth_alias", "wpn=" + wpn + ";mode=carrier_override" );
        }
        player give_max_ammo( wpn );

        if ( !isdefined( no_switch ) || !no_switch )
            player switchtoweapon( wpn );

        rogue_tg_log_player_state( player, "truth_granted", wpn );

        if ( !isdefined( player.rogue_tg_watcher ) )
        {
            player.rogue_tg_watcher = true;
            player thread rogue_thundergun_fire_watcher();
        }

        return true;
    }

    return false;
}

rogue_try_give_thundergun_proxy(player, use_upgraded, no_switch)
{
    if ( !isdefined( player ) || !isplayer( player ) )
        return false;

    carriers = [];
    carriers[0] = "ak74u_zm";

    if ( isdefined( use_upgraded ) && use_upgraded )
        carriers[1] = "ak74u_upgraded_zm";

    for ( ci = 0; ci < carriers.size; ci++ )
    {
        carrier = carriers[ci];
        inc = maps\mp\zombies\_zm_weapons::is_weapon_included( carrier );
        inc_or_base = inc;
        if ( isdefined( maps\mp\zombies\_zm_weapons::is_weapon_or_base_included ) )
            inc_or_base = maps\mp\zombies\_zm_weapons::is_weapon_or_base_included( carrier );
        can_use = player player_can_use_content( carrier );
        had_before = player hasweapon( carrier );
        rogue_log_event( "tg_proxy_attempt", "carrier=" + carrier + ";idx=" + ci + ";upg_req=" + ( isdefined( use_upgraded ) && use_upgraded ) + ";inc=" + inc + ";inc_or_base=" + inc_or_base + ";can_use=" + can_use + ";had_before=" + had_before + ";cur=" + player getcurrentweapon() );

        gave_ok = player try_give_loadout_weapon( carrier );
        has_after = player hasweapon( carrier );
        inv_count = player getweaponslist( 1 ).size;
        rogue_log_event( "tg_proxy_result", "carrier=" + carrier + ";idx=" + ci + ";ok=" + gave_ok + ";has_after=" + has_after + ";inv_count=" + inv_count + ";cur=" + player getcurrentweapon() );

        if ( !has_after )
        {
            rogue_log_event( "tg_proxy_fail_reason", "carrier=" + carrier + ";idx=" + ci + ";reason=grant_failed;inc=" + inc + ";inc_or_base=" + inc_or_base + ";can_use=" + can_use + ";cur=" + player getcurrentweapon() );
            continue;
        }

        player.rogue_tg_proxy_enabled = true;
        player.rogue_tg_proxy_carrier = carrier;
        player give_max_ammo( carrier );

        if ( !isdefined( no_switch ) || !no_switch )
            player switchtoweapon( carrier );

        rogue_tg_log_player_state( player, "proxy_granted", carrier );

        if ( !isdefined( player.rogue_tg_watcher ) )
        {
            player.rogue_tg_watcher = true;
            player thread rogue_thundergun_fire_watcher();
        }

        return true;
    }

    return false;
}

rogue_clone_weapon_entry(src)
{
    dst = spawnstruct();

    if ( !isdefined( src ) )
        return dst;

    keys = getarraykeys( src );
    // Guard against sparse/huge key arrays that can trigger script watchdog stalls.
    copy_cap = keys.size;
    if ( copy_cap > 512 )
        copy_cap = 512;

    for ( i = 0; i < copy_cap; i++ )
    {
        if ( !isdefined( keys[i] ) )
            continue;

        dst[keys[i]] = src[keys[i]];
    }

    // Ensure critical identity fields survive even when capped.
    if ( !isdefined( dst.weapon_name ) && isdefined( src.weapon_name ) )
        dst.weapon_name = src.weapon_name;

    if ( !isdefined( dst.base_weapon ) && isdefined( src.base_weapon ) )
        dst.base_weapon = src.base_weapon;

    if ( !isdefined( dst.upgrade_name ) && isdefined( src.upgrade_name ) )
        dst.upgrade_name = src.upgrade_name;

    return dst;
}

rogue_tag_weapon_entry(entry, weapon_name, upgrade_name)
{
    if ( !isdefined( entry ) )
        return;

    entry.weapon_name = weapon_name;
    entry.base_weapon = weapon_name;
    entry.upgrade_name = upgrade_name;
}

rogue_register_thundergun_with_zm_weapons()
{
    if ( !isdefined( level.zombie_weapons ) )
        return false;

    changed = 0;
    donor_base = "";
    donor_upg = "";

    if ( isdefined( level.zombie_weapons["thundergun_zm"] ) )
        donor_base = "thundergun_zm";
    else if ( isdefined( level.zombie_weapons["ray_gun_zm"] ) )
        donor_base = "ray_gun_zm";
    // Do not fall back to scanning all weapon keys here. On some builds this can
    // be extremely large/sparse and trip the script watchdog.

    if ( isdefined( level.zombie_weapons["thundergun_upgraded_zm"] ) )
        donor_upg = "thundergun_upgraded_zm";
    else if ( isdefined( level.zombie_weapons["ray_gun_upgraded_zm"] ) )
        donor_upg = "ray_gun_upgraded_zm";
    else if ( donor_base != "" && isdefined( level.zombie_weapons[donor_base] ) && isdefined( level.zombie_weapons[donor_base].upgrade_name ) && isdefined( level.zombie_weapons[level.zombie_weapons[donor_base].upgrade_name] ) )
        donor_upg = level.zombie_weapons[donor_base].upgrade_name;

    donor_hint = "ZMUI_WEAPON_RAYGUN";
    donor_cost = 950;
    donor_vox = "ray_gun";
    donor_vox_response = "";
    donor_ammo_cost = 500;
    donor_in_box = 0;

    if ( donor_base != "" && isdefined( level.zombie_weapons[donor_base] ) )
    {
        d = level.zombie_weapons[donor_base];

        if ( isdefined( d.hint ) && d.hint != "" )
            donor_hint = d.hint;

        if ( isdefined( d.cost ) )
            donor_cost = d.cost;

        if ( isdefined( d.vox ) )
            donor_vox = d.vox;

        if ( isdefined( d.vox_response ) )
            donor_vox_response = d.vox_response;

        if ( isdefined( d.ammo_cost ) )
            donor_ammo_cost = d.ammo_cost;

        if ( isdefined( d.is_in_box ) )
            donor_in_box = d.is_in_box;

        if ( donor_upg == "" && isdefined( d.upgrade_name ) && d.upgrade_name != "" )
            donor_upg = d.upgrade_name;
    }

    // Preferred path: register via stock ZM weapon registry APIs.
    // This keeps zombie_include_weapons/zombie_weapons_upgraded consistent.
    native_registered = false;
    if ( isdefined( maps\mp\zombies\_zm_weapons::include_zombie_weapon ) && isdefined( maps\mp\zombies\_zm_weapons::add_zombie_weapon ) )
    {
        maps\mp\zombies\_zm_weapons::include_zombie_weapon( "thundergun_zm", donor_in_box );
        maps\mp\zombies\_zm_weapons::include_zombie_weapon( "thundergun_upgraded_zm", 0 );

        if ( !isdefined( level.zombie_weapons["thundergun_zm"] ) )
            changed = 1;

        maps\mp\zombies\_zm_weapons::add_zombie_weapon( "thundergun_zm", "thundergun_upgraded_zm", donor_hint, donor_cost, donor_vox, donor_vox_response, donor_ammo_cost, 0 );
        native_registered = true;
    }

    // Normalize missing structs even when native registration succeeds.
    // On some builds, add_zombie_weapon populates include/upgrade maps but leaves
    // the upgraded weapon struct undefined, which can break grant resolution.
    if ( !isdefined( level.zombie_weapons["thundergun_zm"] ) )
    {
        if ( donor_base != "" && isdefined( level.zombie_weapons[donor_base] ) )
            level.zombie_weapons["thundergun_zm"] = rogue_clone_weapon_entry( level.zombie_weapons[donor_base] );
        else
            level.zombie_weapons["thundergun_zm"] = spawnstruct();
        changed = 1;
    }

    if ( !isdefined( level.zombie_weapons["thundergun_upgraded_zm"] ) )
    {
        if ( donor_upg != "" && isdefined( level.zombie_weapons[donor_upg] ) )
            level.zombie_weapons["thundergun_upgraded_zm"] = rogue_clone_weapon_entry( level.zombie_weapons[donor_upg] );
        else if ( donor_base != "" && isdefined( level.zombie_weapons[donor_base] ) )
            level.zombie_weapons["thundergun_upgraded_zm"] = rogue_clone_weapon_entry( level.zombie_weapons[donor_base] );
        else
            level.zombie_weapons["thundergun_upgraded_zm"] = spawnstruct();
        changed = 1;
    }

    if ( isdefined( level.zombie_weapons["thundergun_zm"] ) )
        rogue_tag_weapon_entry( level.zombie_weapons["thundergun_zm"], "thundergun_zm", "thundergun_upgraded_zm" );

    if ( isdefined( level.zombie_weapons["thundergun_upgraded_zm"] ) )
        rogue_tag_weapon_entry( level.zombie_weapons["thundergun_upgraded_zm"], "thundergun_upgraded_zm", "thundergun_upgraded_zm" );

    if ( !isdefined( level.rogue_tg_registry_log_count ) )
        level.rogue_tg_registry_log_count = 0;

    if ( changed || level.rogue_tg_registry_log_count < 4 )
    {
        has_stock = isdefined( level.zombie_weapons["thundergun_zm"] );
        has_stock_upg = isdefined( level.zombie_weapons["thundergun_upgraded_zm"] );
        has_inc_stock = isdefined( level.zombie_include_weapons ) && isdefined( level.zombie_include_weapons["thundergun_zm"] );
        has_upg_map_stock = isdefined( level.zombie_weapons_upgraded ) && isdefined( level.zombie_weapons_upgraded["thundergun_upgraded_zm"] );

        rogue_log_event( "tg_registry", "changed=" + changed + ";native=" + native_registered + ";has_stock=" + has_stock + ";has_stock_upg=" + has_stock_upg + ";inc_stock=" + has_inc_stock + ";upg_stock=" + has_upg_map_stock );
        level.rogue_tg_registry_log_count++;
    }

    return isdefined( level.zombie_weapons["thundergun_zm"] );
}

rogue_precache_thundergun_items()
{
    if ( isdefined( level.rogue_tg_precached ) && level.rogue_tg_precached )
        return;

    // Viewhands swap model used for the BO3 full-rig port.
    if ( 0 != getdvarint( "rogue_tg_viewhands_enable" ) )
        precachemodel( "rogue_tg_viewhands" );

    precacheitem( "thundergun_zm" );
    precacheitem( "thundergun_upgraded_zm" );
    level.rogue_tg_precached = true;
    rogue_log_event( "tg_step", "stage=precache_done" );
}

rogue_thundergun_ensure_vars()
{
    if ( isdefined( level.rogue_tg_vars_set ) )
        return;
    level.rogue_tg_vars_set = true;

    if ( !isdefined( level.zombie_vars ) )
        level.zombie_vars = [];

    level.zombie_vars["thundergun_cylinder_radius"] = 180;
    level.zombie_vars["thundergun_fling_range"] = 480;
    level.zombie_vars["thundergun_gib_range"] = 900;
    level.zombie_vars["thundergun_gib_damage"] = 75;
    level.zombie_vars["thundergun_knockdown_range"] = 1200;
    level.zombie_vars["thundergun_knockdown_damage"] = 15;

    // Truth-lane registration bypass: use a known registered carrier alias.
    level.rogue_tg_truth_weapon = "ak74u_zm";
    level.rogue_tg_truth_weapon_upg = "ak74u_upgraded_zm";

    level.thundergun_gib_refs = [];
    level.thundergun_gib_refs[0] = "guts";
    level.thundergun_gib_refs[1] = "right_arm";
    level.thundergun_gib_refs[2] = "left_arm";
}

rogue_thundergun_fire_watcher()
{
    self endon( "disconnect" );

    for (;;)
    {
        self waittill( "weapon_fired" );
        w = self getcurrentweapon();
        is_proxy = false;
        if ( isdefined( self.rogue_tg_proxy_enabled ) && self.rogue_tg_proxy_enabled && isdefined( self.rogue_tg_proxy_carrier ) && w == self.rogue_tg_proxy_carrier )
            is_proxy = true;

        if ( w == "thundergun_zm" || w == "thundergun_upgraded_zm" || is_proxy )
        {
            if ( is_proxy )
                rogue_log_event( "tg_proxy_fire", "carrier=" + w + ";cur=" + self getcurrentweapon() );
            self thread rogue_thundergun_fired();
        }
    }
}

rogue_thundergun_fired()
{
    physicsexplosioncylinder( self.origin, 600, 240, 1 );

    view_pos = self getweaponmuzzlepoint();
    forward = self getweaponforwarddir();
    end_pos = view_pos + vectorscale( forward, level.zombie_vars["thundergun_knockdown_range"] );

    zombies = maps\mp\_utility::get_array_of_closest( view_pos, maps\mp\zombies\_zm_utility::get_round_enemy_array(), undefined, undefined, level.zombie_vars["thundergun_knockdown_range"] );
    if ( !isdefined( zombies ) )
        return;

    knockdown_sq = level.zombie_vars["thundergun_knockdown_range"] * level.zombie_vars["thundergun_knockdown_range"];
    fling_sq = level.zombie_vars["thundergun_fling_range"] * level.zombie_vars["thundergun_fling_range"];
    cyl_sq = level.zombie_vars["thundergun_cylinder_radius"] * level.zombie_vars["thundergun_cylinder_radius"];
    fling_i = 0;

    for ( i = 0; i < zombies.size; i++ )
    {
        if ( !isdefined( zombies[i] ) || !isalive( zombies[i] ) )
            continue;

        zpos = zombies[i] getcentroid();
        dsq = distancesquared( view_pos, zpos );
        if ( dsq > knockdown_sq )
            continue;

        normal = vectornormalize( zpos - view_pos );
        if ( vectordot( forward, normal ) <= 0 )
            continue;

        radial = pointonsegmentnearesttopoint( view_pos, end_pos, zpos );
        if ( distancesquared( zpos, radial ) > cyl_sq )
            continue;

        if ( 0 == zombies[i] damageconetrace( view_pos, self ) )
            continue;

        if ( dsq < fling_sq )
        {
            dist_mult = ( fling_sq - dsq ) / fling_sq;
            fling_vec = vectornormalize( zpos - view_pos );
            if ( 5000 < dsq )
                fling_vec = fling_vec + vectornormalize( zpos - radial );
            fling_vec = ( fling_vec[0], fling_vec[1], abs( fling_vec[2] ) );
            fling_vec = vectorscale( fling_vec, 100 + 100 * dist_mult );
            zombies[i] thread rogue_thundergun_fling( self, fling_vec, fling_i );
            fling_i++;
        }
        else
        {
            zombies[i] thread rogue_thundergun_knockdown( self );
        }
    }
}

rogue_thundergun_fling( player, fling_vec, index )
{
    if ( !isdefined( self ) || !isalive( self ) )
        return;

    self dodamage( self.health + 666, player.origin, player );

    if ( self.health <= 0 )
    {
        points = 10;
        if ( !index )
            points = 50;
        else if ( 1 == index )
            points = 30;

        player maps\mp\zombies\_zm_score::player_add_points( "thundergun_fling", points );
        self startragdoll();
        self launchragdoll( fling_vec );
        self.thundergun_death = 1;
    }
}

rogue_thundergun_knockdown( player )
{
    self endon( "death" );

    if ( !isdefined( self ) || !isalive( self ) )
        return;

    self dodamage( level.zombie_vars["thundergun_knockdown_damage"], player.origin, player );
    self dodamage( level.zombie_vars["thundergun_knockdown_damage"], player.origin, player );
}

rogue_extract_start_entry(raw_text)
{
    cmd_text = tolower( "" + raw_text );

    if ( !issubstr( cmd_text, "start" ) )
        return -1;

    parts = strtok( cmd_text, " " );
    if ( !isdefined( parts ) || parts.size < 1 )
        return -1;

    start_index = -1;
    for ( i = 0; i < parts.size; i++ )
    {
        token = parts[i];

        if ( !isdefined( token ) || token == "" )
            continue;

        if ( token == ".start" || token == "start" || token == "/start" )
        {
            start_index = i;
            break;
        }
    }

    if ( start_index < 0 )
        return -1;

    entry_fee = 1000;

    if ( start_index + 1 < parts.size )
        entry_fee = extract_first_int( parts[start_index + 1], 1000 );
    else
        entry_fee = extract_first_int( parts[start_index], 1000 );

    if ( entry_fee < 0 )
        entry_fee = 0;

    if ( entry_fee > 250000 )
        entry_fee = 250000;

    return entry_fee;
}

extract_first_int(text, default_value)
{
    if ( !isdefined( text ) || text == "" )
        return default_value;

    digits = "";
    seen_digit = 0;

    for ( i = 0; i < text.size; i++ )
    {
        ch = getsubstr( text, i, i + 1 );

        if ( is_digit_char( ch ) )
        {
            seen_digit = 1;
            digits += ch;
            continue;
        }

        if ( seen_digit )
            break;
    }

    if ( digits == "" )
        return default_value;

    return int( digits );
}

is_digit_char(ch)
{
    if ( ch == "0" || ch == "1" || ch == "2" || ch == "3" || ch == "4" || ch == "5" || ch == "6" || ch == "7" || ch == "8" || ch == "9" )
        return true;

    return false;
}

rogue_start_gauntlet(player, entry_fee)
{
    if ( isdefined( level.rogue_started ) && level.rogue_started )
    {
        player iprintln( "^3Rogue Gauntlet is already running." );
        return;
    }

    if ( !isdefined( player.score ) || player.score < entry_fee )
    {
        player iprintlnbold( "^1Need " + entry_fee + " points to start. You have " + player.score + "." );
        return;
    }

    if ( entry_fee > 0 )
        player.score = player.score - entry_fee;

    level.rogue_entry_fee = entry_fee;
    level.rogue_started = 1;
    level.rogue_completed = 0;
    level.rogue_target_round = 1;
    level.rogue_last_round_started = undefined;
    level.rogue_panzer_mode = 1;
    level.rogue_loop_running = 0;
    level.rogue_wave_spawning = 0;
    rogue_wait_for_base_spawners( 2.0 );
    pool = rogue_get_panzer_spawner_pool();
    rogue_log_event( "gauntlet_start_try", "entry=" + entry_fee + ";pool=" + pool.size + ";zsp=" + rogue_get_spawner_count_text() );

    if ( !isdefined( pool ) || pool.size < 1 )
    {
        rogue_log_event( "gauntlet_start_blocked", "reason=no_spawner_pool;entry=" + entry_fee + ";zsp=" + rogue_get_spawner_count_text() );
        player iprintlnbold( "^1No panzer/zombie spawners ready on this map variant. Panzer-only mode cannot start." );
        level.rogue_started = 0;
        level.rogue_panzer_mode = 0;
        return;
    }

    rogue_broadcast( "^2Panzer runtime ready:^7 " + pool.size + " mech spawners detected." );
    rogue_broadcast( "^2Rogue Gauntlet started^7 by " + player.name + " (entry " + entry_fee + ")." );
    rogue_pause_zombie_spawns();
    level thread rogue_panzer_spawn_lockdown();
    level thread rogue_panzer_gauntlet_loop( player );
}

rogue_broadcast(text)
{
    players = getplayers();

    for ( i = 0; i < players.size; i++ )
    {
        if ( isdefined( players[i] ) )
            players[i] iprintlnbold( text );
    }
}

rogue_round_start_custom()
{
    if ( isdefined( level.rogue_prev_round_start_custom ) && level.rogue_prev_round_start_custom != ::rogue_round_start_custom )
        [[ level.rogue_prev_round_start_custom ]]();

    if ( !isdefined( level.rogue_started ) || !level.rogue_started )
    {
        rogue_pause_zombie_spawns();
        return;
    }

    if ( isdefined( level.rogue_completed ) && level.rogue_completed )
    {
        rogue_pause_zombie_spawns();
        return;
    }

    if ( level.rogue_target_round > level.rogue_round_goal )
    {
        level.rogue_started = 0;
        level.rogue_completed = 1;
        rogue_pause_zombie_spawns();
        return;
    }
    // Panzer gauntlet manages spawns itself; keep normal zombie rounds disabled.
    rogue_pause_zombie_spawns();
}

rogue_round_end_monitor()
{
    for (;;)
    {
        level waittill( "end_of_round" );

        if ( isdefined( level.rogue_panzer_mode ) && level.rogue_panzer_mode )
            continue;

        if ( !isdefined( level.rogue_started ) || !level.rogue_started )
            continue;

        cleared_round = level.rogue_target_round;

        if ( cleared_round >= level.rogue_round_goal )
        {
            level.rogue_started = 0;
            level.rogue_completed = 1;
            rogue_pause_zombie_spawns();
            rogue_broadcast( "^2Gauntlet clear!^7 You survived 10 rounds." );
            continue;
        }

        rogue_pause_zombie_spawns();
        level.rogue_target_round = cleared_round + 1;
        level.rogue_last_round_started = undefined;
        level thread rogue_begin_between_round_boon_phase( cleared_round );
    }
}

rogue_begin_between_round_boon_phase(cleared_round)
{
    if ( isdefined( level.rogue_boon_in_progress ) && level.rogue_boon_in_progress )
        return;

    level.rogue_boon_in_progress = 1;
    players = getplayers();

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isalive( players[i] ) )
            continue;

        players[i].rogue_boon_pick_done_round = undefined;
        players[i] thread rogue_player_pick_boon( cleared_round );
    }

    end_time = gettime() + 25000;

    for (;;)
    {
        all_done = 1;
        players = getplayers();

        for ( i = 0; i < players.size; i++ )
        {
            if ( !isdefined( players[i] ) || !isalive( players[i] ) )
                continue;

            if ( !isdefined( players[i].rogue_boon_pick_done_round ) || players[i].rogue_boon_pick_done_round != cleared_round )
            {
                all_done = 0;
                break;
            }
        }

        if ( all_done || gettime() >= end_time )
            break;

        wait 0.05;
    }

    level.rogue_boon_in_progress = 0;

    if ( isdefined( level.rogue_started ) && level.rogue_started && !( isdefined( level.rogue_completed ) && level.rogue_completed ) && !( isdefined( level.rogue_panzer_mode ) && level.rogue_panzer_mode ) )
        rogue_resume_zombie_spawns();
}

rogue_panzer_gauntlet_loop(owner_player)
{
    if ( isdefined( level.rogue_loop_running ) && level.rogue_loop_running )
        return;

    level.rogue_loop_running = 1;
    round_num = 1;
    rogue_pause_zombie_spawns();

    while ( isdefined( level.rogue_started ) && level.rogue_started && round_num <= level.rogue_round_goal )
    {
        level.rogue_target_round = round_num;
        level.round_number = round_num;
        rogue_apply_round_scaling( round_num );
        rogue_pause_zombie_spawns();

        players = getplayers();
        for ( i = 0; i < players.size; i++ )
        {
            if ( !isdefined( players[i] ) || !isalive( players[i] ) )
                continue;

            players[i] rogue_apply_round_start_boons();
        }

        spawn_count = rogue_get_panzer_spawn_count( round_num );
        rogue_broadcast( "^3Gauntlet Round " + round_num + "^7: spawning ^1" + spawn_count + "^7 panzers." );

        spawned = rogue_spawn_panzer_wave( round_num, spawn_count );
        if ( spawned.size < 1 )
        {
            pool_size = 0;
            failed_count = 0;
            fail_reason = "unknown";
            fail_path = "unknown";

            if ( isdefined( level.rogue_last_panzer_pool_size ) )
                pool_size = level.rogue_last_panzer_pool_size;

            if ( isdefined( level.rogue_last_panzer_failed_spawns ) )
                failed_count = level.rogue_last_panzer_failed_spawns;

            if ( isdefined( level.rogue_last_panzer_fail_reason ) )
                fail_reason = level.rogue_last_panzer_fail_reason;

            if ( isdefined( level.rogue_last_panzer_spawn_path ) )
                fail_path = level.rogue_last_panzer_spawn_path;

            if ( fail_reason == "spawn_failed" )
                rogue_broadcast( "^1Panzer spawn failed on this map^7 (pool " + pool_size + ", failed " + failed_count + ", path " + fail_path + ")." );
            else
                rogue_broadcast( "^1No Panzer-compatible spawners found on this map^7 (pool " + pool_size + ")." );

            level.rogue_started = 0;
            level.rogue_completed = 0;
            break;
        }

        rogue_wait_for_panzer_wave_clear( spawned, round_num );

        if ( !isdefined( level.rogue_started ) || !level.rogue_started )
            break;

        if ( round_num >= level.rogue_round_goal )
        {
            level.rogue_started = 0;
            level.rogue_completed = 1;
            rogue_pause_zombie_spawns();
            rogue_broadcast( "^2Gauntlet clear!^7 You survived 10 rounds." );
            break;
        }

        rogue_pause_zombie_spawns();
        level thread rogue_begin_between_round_boon_phase( round_num );

        while ( isdefined( level.rogue_boon_in_progress ) && level.rogue_boon_in_progress )
            wait 0.05;

        round_num++;
        wait 0.5;
    }

    rogue_pause_zombie_spawns();
    level.rogue_loop_running = 0;
}

rogue_get_panzer_spawn_count(round_num)
{
    if ( round_num < 1 )
        round_num = 1;

    base_count = 1 + int( ( round_num - 1 ) / 3 );
    random_count = randomintrange( 0, 3 );

    if ( round_num >= 6 )
        random_count = random_count + randomintrange( 0, 2 );

    total = base_count + random_count;

    if ( total < 1 )
        total = 1;

    if ( total > 9 )
        total = 9;

    return total;
}

rogue_is_town_variant_map()
{
    map_name = tolower( getdvar( "mapname" ) );

    if ( !isdefined( map_name ) || map_name == "" )
        return false;

    if ( map_name == "so_zsurvival_zm_transit" )
        return true;

    if ( map_name == "so_zclassic_zm_transit" )
        return true;

    if ( map_name == "zm_transit" )
        return true;

    if ( map_name == "zm_nuked" )
        return true;

    return false;
}

rogue_get_spawn_center_origin()
{
    locs = getstructarray( "zombie_location", "script_noteworthy" );

    if ( !isdefined( locs ) || locs.size < 1 )
        locs = getstructarray( "spawn_location", "script_noteworthy" );

    if ( !isdefined( locs ) || locs.size < 1 )
        return undefined;

    sx = 0.0;
    sy = 0.0;
    sz = 0.0;
    c = 0;

    for ( i = 0; i < locs.size; i++ )
    {
        if ( !isdefined( locs[i] ) || !isdefined( locs[i].origin ) )
            continue;

        sx = sx + locs[i].origin[0];
        sy = sy + locs[i].origin[1];
        sz = sz + locs[i].origin[2];
        c++;
    }

    if ( c < 1 )
        return undefined;

    return ( sx / c, sy / c, ( sz / c ) + 36.0 );
}

rogue_pick_nearest_spawner(pool, target_origin)
{
    if ( !isdefined( pool ) || pool.size < 1 )
        return undefined;

    if ( !isdefined( target_origin ) )
        return pool[0];

    best = undefined;
    best_dist_sq = 999999999.0;

    for ( i = 0; i < pool.size; i++ )
    {
        if ( !isdefined( pool[i] ) || !isdefined( pool[i].spawner ) || !isdefined( pool[i].spawner.origin ) )
            continue;

        dx = pool[i].spawner.origin[0] - target_origin[0];
        dy = pool[i].spawner.origin[1] - target_origin[1];
        dz = pool[i].spawner.origin[2] - target_origin[2];
        dist_sq = dx * dx + dy * dy + dz * dz;

        if ( !isdefined( best ) || dist_sq < best_dist_sq )
        {
            best = pool[i];
            best_dist_sq = dist_sq;
        }
    }

    if ( !isdefined( best ) )
        return pool[0];

    return best;
}

rogue_town_panzer_debug_spawn_once()
{
    if ( getdvarint( "rogue_town_debug_spawn" ) != 1 )
        return;

    if ( !rogue_is_town_variant_map() )
        return;

    wait 1.0;

    tries = 0;
    while ( getplayers().size < 1 && tries < 300 )
    {
        wait 0.05;
        tries++;
    }

    wait 2.0;

    center = rogue_get_spawn_center_origin();

    if ( !rogue_init_mechz_runtime_for_all_maps() )
    {
        reason = "unknown";

        if ( isdefined( level.rogue_mechz_runtime_fail_reason ) && level.rogue_mechz_runtime_fail_reason != "" )
            reason = level.rogue_mechz_runtime_fail_reason;

        rogue_broadcast( "^1Town Panzer debug:^7 mech runtime init failed (" + reason + "), trying direct actor spawn..." );
        ai = rogue_spawn_direct_mech_actor( center, 1 );

        if ( !isdefined( ai ) || !isalive( ai ) )
        {
            rogue_broadcast( "^1Town Panzer debug:^7 direct actor spawn failed, trying proxy spawner..." );
            ai = rogue_spawn_proxy_mech_actor( center, 1 );

            if ( !isdefined( ai ) || !isalive( ai ) )
            {
                rogue_broadcast( "^1Town Panzer debug:^7 proxy spawner mech spawn failed." );
                return;
            }

            if ( !rogue_is_mech_actor_class( ai ) )
            {
                rogue_broadcast( "^1Town Panzer debug:^7 proxy spawned non-mech actor: " + rogue_safe_str( ai.classname ) );
                return;
            }

            ai.rogue_is_panzer = 1;
            ai.rogue_panzer_type = "mechz";
            ai.rogue_round_spawned = 1;
            rogue_tune_panzer_actor( ai, 1, "mechz" );
            rogue_broadcast( "^2Town Panzer debug:^7 proxy mech spawn success (" + rogue_safe_str( ai.classname ) + ")." );
            return;
        }

        if ( !rogue_is_mech_actor_class( ai ) )
        {
            rogue_broadcast( "^1Town Panzer debug:^7 direct spawn returned non-mech actor: " + rogue_safe_str( ai.classname ) );
            return;
        }

        ai.rogue_is_panzer = 1;
        ai.rogue_panzer_type = "mechz";
        ai.rogue_round_spawned = 1;
        rogue_tune_panzer_actor( ai, 1, "mechz" );
        rogue_broadcast( "^2Town Panzer debug:^7 direct mech spawn success (" + rogue_safe_str( ai.classname ) + ")." );
        return;
    }

    pool = rogue_get_panzer_spawner_pool();
    if ( !isdefined( pool ) || pool.size < 1 )
    {
        rogue_broadcast( "^1Town Panzer debug:^7 no mechz_spawner found (zombie_spawners=" + rogue_get_spawner_count_text() + "), trying direct actor spawn..." );
        ai = rogue_spawn_direct_mech_actor( center, 1 );

        if ( !isdefined( ai ) || !isalive( ai ) )
        {
            rogue_broadcast( "^1Town Panzer debug:^7 direct actor spawn failed, trying proxy spawner..." );
            ai = rogue_spawn_proxy_mech_actor( center, 1 );

            if ( !isdefined( ai ) || !isalive( ai ) )
            {
                rogue_broadcast( "^1Town Panzer debug:^7 proxy spawner mech spawn failed." );
                return;
            }

            if ( !rogue_is_mech_actor_class( ai ) )
            {
                rogue_broadcast( "^1Town Panzer debug:^7 proxy spawned non-mech actor: " + rogue_safe_str( ai.classname ) );
                return;
            }

            ai.rogue_is_panzer = 1;
            ai.rogue_panzer_type = "mechz";
            ai.rogue_round_spawned = 1;
            rogue_tune_panzer_actor( ai, 1, "mechz" );
            rogue_broadcast( "^2Town Panzer debug:^7 proxy mech spawn success (" + rogue_safe_str( ai.classname ) + ")." );
            return;
        }

        if ( !rogue_is_mech_actor_class( ai ) )
        {
            rogue_broadcast( "^1Town Panzer debug:^7 direct spawn returned non-mech actor: " + rogue_safe_str( ai.classname ) );
            return;
        }

        ai.rogue_is_panzer = 1;
        ai.rogue_panzer_type = "mechz";
        ai.rogue_round_spawned = 1;
        rogue_tune_panzer_actor( ai, 1, "mechz" );
        rogue_broadcast( "^2Town Panzer debug:^7 direct mech spawn success (" + rogue_safe_str( ai.classname ) + ")." );
        return;
    }

    pick = rogue_pick_nearest_spawner( pool, center );

    if ( !isdefined( pick ) || !isdefined( pick.spawner ) )
    {
        rogue_broadcast( "^1Town Panzer debug:^7 failed to pick spawner." );
        return;
    }

    ai = rogue_try_spawn_mech_via_utility( pick.spawner, 1 );

    if ( ( !isdefined( ai ) || !isalive( ai ) || !rogue_is_mech_actor_class( ai ) ) && isdefined( center ) )
        ai = rogue_spawn_direct_mech_actor( center, 1 );

    if ( ( !isdefined( ai ) || !isalive( ai ) || !rogue_is_mech_actor_class( ai ) ) && isdefined( center ) )
        ai = rogue_spawn_proxy_mech_actor( center, 1 );

    if ( !isdefined( ai ) || !isalive( ai ) )
    {
        rogue_broadcast( "^1Town Panzer debug:^7 spawnactor failed (undefined AI)." );
        return;
    }

    if ( isdefined( center ) )
        ai forceteleport( center );

    if ( !rogue_is_mech_actor_class( ai ) )
    {
        rogue_broadcast( "^1Town Panzer debug:^7 fallback actor spawned: " + rogue_safe_str( ai.classname ) );
        return;
    }

    ai.rogue_is_panzer = 1;
    ai.rogue_panzer_type = "mechz";
    ai.rogue_round_spawned = 1;
    rogue_tune_panzer_actor( ai, 1, "mechz" );
    rogue_broadcast( "^2Town Panzer debug:^7 mech spawn success (" + rogue_safe_str( ai.classname ) + ")." );
}

rogue_get_spawner_count_text()
{
    if ( isdefined( level.zombie_spawners ) )
        return "" + level.zombie_spawners.size;

    return "undef";
}

rogue_spawn_direct_mech_actor(spawn_origin, round_num)
{
    if ( !isdefined( spawn_origin ) )
        spawn_origin = rogue_get_alive_player_origin();

    if ( rogue_is_town_variant_map() && isdefined( spawn_origin ) )
    {
        safe_origin = rogue_pick_safe_mech_spawn_origin( spawn_origin );
        if ( isdefined( safe_origin ) )
            spawn_origin = safe_origin;
    }

    if ( !isdefined( spawn_origin ) && !rogue_is_town_variant_map() )
    {
        loc = rogue_get_nearest_mech_location( undefined );
        if ( isdefined( loc ) && isdefined( loc.origin ) )
            spawn_origin = loc.origin;
    }

    if ( !isdefined( spawn_origin ) && rogue_is_town_variant_map() )
        spawn_origin = rogue_pick_safe_mech_spawn_origin( rogue_get_alive_player_origin() );

    if ( !isdefined( spawn_origin ) )
        spawn_origin = ( 0, 0, 0 );

    rogue_log_event( "direct_try", "round=" + round_num + ";origin=" + rogue_safe_str( spawn_origin ) );

    while ( getfreeactorcount() < 1 )
        wait 0.05;

    ai = spawn( "actor_zm_tomb_mech_zombie", spawn_origin );

    if ( !isdefined( ai ) )
    {
        rogue_log_event( "direct_fail", "round=" + round_num + ";origin=" + rogue_safe_str( spawn_origin ) );
        return undefined;
    }

    if ( isdefined( round_num ) )
        ai._starting_round_number = round_num;

    ai.aiteam = level.zombie_team;
    ai clearentityowner();
    ai forceteleport( spawn_origin );
    ai show();
    ai.rogue_is_panzer = 1;
    ai.rogue_panzer_type = "mechz";
    ai.rogue_spawn_grace_until = gettime() + 5000;
    ai.rogue_spawn_source = "direct";
    ai.rogue_needs_mech_activation = 1;
    rogue_log_event( "direct_ok", "round=" + round_num + ";class=" + rogue_safe_str( ai.classname ) + ";origin=" + rogue_safe_str( spawn_origin ) );
    return ai;
}

rogue_spawn_proxy_mech_actor(spawn_origin, round_num)
{
    if ( !isdefined( level.zombie_spawners ) || level.zombie_spawners.size < 1 )
        return undefined;

    pick = rogue_pick_nearest_zombie_spawner( spawn_origin );

    if ( !isdefined( pick ) )
        return undefined;

    ai = rogue_try_spawn_mech_via_utility( pick, round_num );

    if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
        return ai;

    if ( isdefined( pick.origin ) )
    {
        ai = rogue_spawn_direct_mech_actor( pick.origin, round_num );

        if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
            return ai;
    }

    return undefined;
}

rogue_pick_nearest_zombie_spawner(target_origin)
{
    if ( !isdefined( level.zombie_spawners ) || level.zombie_spawners.size < 1 )
        return undefined;

    if ( !isdefined( target_origin ) )
        return level.zombie_spawners[0];

    best = undefined;
    best_dist_sq = 999999999.0;

    for ( i = 0; i < level.zombie_spawners.size; i++ )
    {
        s = level.zombie_spawners[i];
        if ( !isdefined( s ) || !isdefined( s.origin ) )
            continue;

        dx = s.origin[0] - target_origin[0];
        dy = s.origin[1] - target_origin[1];
        dz = s.origin[2] - target_origin[2];
        dist_sq = dx * dx + dy * dy + dz * dz;

        if ( !isdefined( best ) || dist_sq < best_dist_sq )
        {
            best = s;
            best_dist_sq = dist_sq;
        }
    }

    if ( !isdefined( best ) )
        return level.zombie_spawners[0];

    return best;
}

rogue_get_panzer_spawner_pool()
{
    mech_pool = [];

    // Strict Panzer mode: mech spawners only.
    mech_spawners = rogue_get_mechz_spawners();
    mech_actor_ents = getentarray( "actor_zm_tomb_mech_zombie", "classname" );
    mech_locations = getentarray( "mechz_location", "script_noteworthy" );
    rogue_log_event( "pool_scan", "mech_spawners=" + mech_spawners.size + ";mech_actor_ents=" + mech_actor_ents.size + ";mech_locations=" + mech_locations.size );

    for ( i = 0; i < mech_spawners.size; i++ )
    {
        if ( !isdefined( mech_spawners[i] ) )
            continue;

        // Only use dedicated mech spawn entities; never recycle live mech actors
        // back into the spawn pool.
        if ( !isdefined( mech_spawners[i].script_noteworthy ) || mech_spawners[i].script_noteworthy != "mechz_spawner" )
            continue;

        entry = spawnstruct();
        entry.spawner = mech_spawners[i];
        entry.type = "mechz";
        mech_pool[mech_pool.size] = entry;
    }

    // Full-port fallback: spawn real mech actor at mechz/zombie locations if no map mech spawner entity exists.
    if ( mech_pool.size < 1 )
    {
        if ( !isdefined( level.zombie_mechz_locations ) || level.zombie_mechz_locations.size < 1 )
            rogue_prepare_mechz_runtime();

        if ( isdefined( level.zombie_mechz_locations ) && level.zombie_mechz_locations.size > 0 )
        {
            for ( i = 0; i < level.zombie_mechz_locations.size; i++ )
            {
                if ( !isdefined( level.zombie_mechz_locations[i] ) || !isdefined( level.zombie_mechz_locations[i].origin ) )
                    continue;

                point = spawnstruct();
                point.origin = level.zombie_mechz_locations[i].origin;
                point.classname = "rogue_mechz_direct_point";
                point.script_noteworthy = "mechz_location";

                entry = spawnstruct();
                entry.spawner = point;
                entry.type = "mechz_direct_point";
                mech_pool[mech_pool.size] = entry;
            }
        }

        if ( mech_pool.size < 1 )
        {
            rogue_wait_for_base_spawners( 0.50 );

            if ( isdefined( level.zombie_spawners ) && level.zombie_spawners.size > 0 )
            {
                for ( i = 0; i < level.zombie_spawners.size; i++ )
                {
                    if ( !isdefined( level.zombie_spawners[i] ) || !isdefined( level.zombie_spawners[i].origin ) )
                        continue;

                    point = spawnstruct();
                    point.origin = level.zombie_spawners[i].origin;
                    point.classname = "rogue_mechz_direct_point";
                    point.script_noteworthy = "zombie_spawner";

                    entry = spawnstruct();
                    entry.spawner = point;
                    entry.type = "mechz_direct_point";
                    mech_pool[mech_pool.size] = entry;
                }
            }
        }
    }

    return mech_pool;
}

rogue_wait_for_base_spawners(timeout_sec)
{
    if ( isdefined( level.zombie_spawners ) && level.zombie_spawners.size > 0 )
        return true;

    if ( !isdefined( timeout_sec ) || timeout_sec < 0.05 )
        timeout_sec = 0.05;

    end_time = gettime() + int( timeout_sec * 1000.0 );

    for (;;)
    {
        level.zombie_spawners = getentarray( "zombie_spawner", "script_noteworthy" );
        if ( isdefined( level.zombie_spawners ) && level.zombie_spawners.size > 0 )
            return true;

        if ( gettime() >= end_time )
            break;

        wait 0.05;
    }

    return false;
}

rogue_add_spawner_entries(pool, noteworthy, boss_type)
{
    spawners = getentarray( noteworthy, "script_noteworthy" );

    for ( i = 0; i < spawners.size; i++ )
    {
        if ( !isdefined( spawners[i] ) )
            continue;

        entry = spawnstruct();
        entry.spawner = spawners[i];
        entry.type = boss_type;
        pool[pool.size] = entry;
    }

    return pool;
}

rogue_pick_boss_spawner(pool, round_num)
{
    if ( !isdefined( pool ) || pool.size < 1 )
        return undefined;

    return pool[randomint( pool.size )];
}

rogue_spawn_panzer_wave(round_num, spawn_count)
{
    spawned = [];
    level.rogue_last_panzer_pool_size = 0;
    level.rogue_last_panzer_failed_spawns = 0;
    level.rogue_last_panzer_fail_reason = "unknown";
    if ( !rogue_init_mechz_runtime_for_all_maps() )
    {
        reason = "unknown";
        if ( isdefined( level.rogue_mechz_runtime_fail_reason ) && level.rogue_mechz_runtime_fail_reason != "" )
            reason = level.rogue_mechz_runtime_fail_reason;

        rogue_log_event( "runtime_init_fail_wave", "round=" + round_num + ";reason=" + reason );
    }

    rogue_wait_for_base_spawners( 1.0 );
    pool = rogue_get_panzer_spawner_pool();
    rogue_cleanup_orphan_mech_actors();
    failed_spawns = 0;
    rogue_log_event( "wave_begin", "round=" + round_num + ";want=" + spawn_count + ";pool=" + pool.size + ";zsp=" + rogue_get_spawner_count_text() );

    if ( !isdefined( pool ) || pool.size < 1 )
    {
        level.rogue_last_panzer_pool_size = 0;
        level.rogue_last_panzer_failed_spawns = 0;
        level.rogue_last_panzer_fail_reason = "pool_empty";
        return spawned;
    }

    level.rogue_last_panzer_pool_size = pool.size;

    level.rogue_wave_spawning = 1;

    for ( i = 0; i < spawn_count; i++ )
    {
        pick = rogue_pick_boss_spawner( pool, round_num );

        if ( !isdefined( pick ) || !isdefined( pick.spawner ) )
        {
            rogue_log_event( "spawn_pick_fail", "round=" + round_num + ";idx=" + i );
            continue;
        }

        spawner = pick.spawner;

        // Never call spawnactor() for panzer waves.
        if ( pick.type == "mechz_direct_point" )
        {
            level.rogue_last_panzer_spawn_path = "direct_point";
            ai = rogue_spawn_direct_mech_actor( spawner.origin, round_num );
        }
        else
        {
            level.rogue_last_panzer_spawn_path = "utility";
            ai = rogue_try_spawn_mech_via_utility( spawner, round_num );
        }

        if ( !isdefined( ai ) || !isalive( ai ) )
        {
            rogue_log_event( "spawnactor_fail", "round=" + round_num + ";type=" + pick.type + ";class=" + rogue_safe_str( spawner.classname ) + ";sn=" + rogue_safe_str( spawner.script_noteworthy ) + ";tn=" + rogue_safe_str( spawner.targetname ) );
            if ( pick.type == "mechz_proxy_spawner" )
                ai = rogue_try_spawn_mech_via_utility( spawner, round_num );
            else if ( pick.type == "mechz_direct_point" )
                ai = rogue_spawn_direct_mech_actor( spawner.origin, round_num );

            if ( ( !isdefined( ai ) || !isalive( ai ) ) && ( pick.type == "mechz" || pick.type == "mechz_proxy_spawner" ) )
            {
                ai = rogue_spawn_direct_mech_actor( spawner.origin, round_num );
                if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
                    level.rogue_last_panzer_spawn_path = "direct_fallback";
            }

            if ( !isdefined( ai ) || !isalive( ai ) )
            {
                rogue_log_event( "spawn_total_fail", "round=" + round_num + ";type=" + pick.type + ";path=" + rogue_safe_str( level.rogue_last_panzer_spawn_path ) );
                failed_spawns++;
                continue;
            }
        }

        if ( pick.type == "mechz_proxy_spawner" && !rogue_is_mech_actor_class( ai ) )
        {
            rogue_log_event( "proxy_wrong_actor", "round=" + round_num + ";class=" + rogue_safe_str( ai.classname ) + ";retry=utility" );
            ai dodamage( ai.health + 10000, ai.origin );
            ai = rogue_try_spawn_mech_via_utility( spawner, round_num );

            if ( !isdefined( ai ) || !isalive( ai ) )
            {
                ai = rogue_spawn_direct_mech_actor( spawner.origin, round_num );
                if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
                    level.rogue_last_panzer_spawn_path = "direct_fallback_after_proxy";
            }

            if ( !isdefined( ai ) || !isalive( ai ) )
            {
                rogue_log_event( "proxy_utility_retry_fail", "round=" + round_num + ";type=" + pick.type );
                failed_spawns++;
                continue;
            }
        }

        if ( !isdefined( ai ) || !isalive( ai ) )
        {
            failed_spawns++;
            continue;
        }

        if ( ( pick.type == "mechz" || pick.type == "mechz_proxy_spawner" || pick.type == "mechz_direct_point" ) && !rogue_is_mech_actor_class( ai ) )
        {
            // Wrong actor type from a mech wave; reject to avoid regular-zombie substitution.
            rogue_log_event( "reject_non_mech", "round=" + round_num + ";class=" + rogue_safe_str( ai.classname ) + ";type=" + pick.type );
            ai dodamage( ai.health + 10000, ai.origin );
            failed_spawns++;
            continue;
        }

        boss_type = pick.type;
        if ( boss_type == "panzer_proxy_spawner" )
            boss_type = "proxy_panzer";
        if ( rogue_is_mech_actor_class( ai ) )
            boss_type = "mechz";

        ai.rogue_is_panzer = 1;
        ai.rogue_panzer_type = boss_type;
        ai.rogue_round_spawned = round_num;
        if ( rogue_is_mech_actor_class( ai ) )
            rogue_force_mech_spawn_near_players( round_num, "wave_spawn", spawner.origin );
        else
            rogue_relocate_panzer_near_players( ai, round_num, boss_type );
        rogue_tune_panzer_actor( ai, round_num, boss_type );
        rogue_log_event( "spawn_post_tune", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";alive=" + isalive( ai ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) + ";origin=" + rogue_safe_str( ai.origin ) );

        is_valid_spawn = rogue_validate_panzer_actor_post_tune( ai, round_num, boss_type );

        if ( !is_valid_spawn && rogue_is_mech_actor_class( ai ) )
        {
            fallback_origin = undefined;
            if ( isdefined( spawner ) && isdefined( spawner.origin ) )
                fallback_origin = spawner.origin;
            if ( !isdefined( fallback_origin ) )
                fallback_origin = rogue_get_alive_player_origin();

            fallback_ai = rogue_spawn_direct_mech_actor( fallback_origin, round_num );
            if ( isdefined( fallback_ai ) && isalive( fallback_ai ) && rogue_is_mech_actor_class( fallback_ai ) )
            {
                ai = fallback_ai;
                ai.rogue_is_panzer = 1;
                ai.rogue_panzer_type = boss_type;
                ai.rogue_round_spawned = round_num;
                rogue_force_mech_spawn_near_players( round_num, "validate_recover", fallback_origin );
                rogue_tune_panzer_actor( ai, round_num, boss_type );
                rogue_log_event( "spawn_post_tune_recover", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";alive=" + isalive( ai ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) + ";origin=" + rogue_safe_str( ai.origin ) );
                is_valid_spawn = rogue_validate_panzer_actor_post_tune( ai, round_num, boss_type );
            }
        }

        if ( !is_valid_spawn )
        {
            failed_spawns++;
            continue;
        }

        rogue_debug_panzer( "panzer spawn ok: classname=" + rogue_safe_str( ai.classname ) + " target=" + rogue_safe_str( ai.targetname ) );
        rogue_log_event( "spawn_ok", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";tn=" + rogue_safe_str( ai.targetname ) );
        ai thread rogue_track_panzer_lifecycle( round_num, boss_type );
        ai thread rogue_track_panzer_death( round_num, boss_type );
        if ( rogue_is_mech_actor_class( ai ) )
            ai thread rogue_mech_runtime_warp_guard( round_num, boss_type );
        spawned[spawned.size] = ai;
        wait 0.18;
    }

    level.rogue_wave_spawning = 0;
    level.rogue_last_panzer_failed_spawns = failed_spawns;
    if ( spawned.size < 1 )
        level.rogue_last_panzer_fail_reason = "spawn_failed";
    else
        level.rogue_last_panzer_fail_reason = "ok";

    rogue_debug_panzer( "spawned panzers: " + spawned.size + " / " + spawn_count + " (pool " + pool.size + ", failed " + failed_spawns + ")" );
    rogue_log_event( "wave_end", "round=" + round_num + ";spawned=" + spawned.size + ";want=" + spawn_count + ";pool=" + pool.size + ";failed=" + failed_spawns + ";reason=" + level.rogue_last_panzer_fail_reason );
    return spawned;
}

rogue_get_alive_player_origin()
{
    players = getplayers();

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isalive( players[i] ) )
            continue;

        if ( isdefined( players[i].origin ) )
            return players[i].origin;
    }

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) )
            continue;

        if ( isdefined( players[i].origin ) )
            return players[i].origin;
    }

    return undefined;
}

rogue_get_alive_player_entity()
{
    players = getplayers();

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isalive( players[i] ) )
            continue;

        if ( isdefined( players[i].origin ) )
            return players[i];
    }

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) )
            continue;

        if ( isdefined( players[i].origin ) )
            return players[i];
    }

    return undefined;
}

rogue_pick_safe_zspawner_for_mech(anchor, min_dist_sq, max_dist_sq, max_z_delta)
{
    if ( !isdefined( level.zombie_spawners ) || level.zombie_spawners.size < 1 )
        return undefined;

    if ( !isdefined( anchor ) )
        return level.zombie_spawners[0];

    best = undefined;
    best_score = 999999999;

    for ( i = 0; i < level.zombie_spawners.size; i++ )
    {
        s = level.zombie_spawners[i];
        if ( !isdefined( s ) || !isdefined( s.origin ) )
            continue;

        dx = s.origin[0] - anchor[0];
        dy = s.origin[1] - anchor[1];
        dz = s.origin[2] - anchor[2];
        dist2d_sq = dx * dx + dy * dy;
        abs_z = abs( dz );

        if ( isdefined( min_dist_sq ) && dist2d_sq < min_dist_sq )
            continue;

        if ( isdefined( max_dist_sq ) && dist2d_sq > max_dist_sq )
            continue;

        if ( isdefined( max_z_delta ) && abs_z > max_z_delta )
            continue;

        candidate = s.origin + ( 0, 0, 28 );
        if ( !rogue_is_safe_mech_spawn_origin( candidate, anchor, min_dist_sq, max_dist_sq, max_z_delta ) )
            continue;

        score = dist2d_sq + ( abs_z * abs_z );
        if ( !isdefined( best ) || score < best_score )
        {
            best = s;
            best_score = score;
        }
    }

    return best;
}

rogue_ground_snap_spawn_origin(origin)
{
    if ( !isdefined( origin ) )
        return undefined;

    trace_start = origin + ( 0, 0, 120 );
    trace_end = origin - ( 0, 0, 1400 );
    tr = physicstrace( trace_start, trace_end, ( -16, -16, -6 ), ( 16, 16, 6 ), undefined );

    if ( isdefined( tr ) && isdefined( tr["position"] ) )
        return tr["position"] + ( 0, 0, 6 );

    return origin;
}

rogue_is_safe_mech_spawn_origin(origin, anchor, min_dist_sq, max_dist_sq, max_z_delta)
{
    if ( !isdefined( origin ) || !isdefined( anchor ) )
        return false;

    snapped = rogue_ground_snap_spawn_origin( origin );
    if ( !isdefined( snapped ) )
        return false;

    dx = snapped[0] - anchor[0];
    dy = snapped[1] - anchor[1];
    dz = snapped[2] - anchor[2];
    dist2d_sq = dx * dx + dy * dy;
    abs_z = abs( dz );

    if ( isdefined( min_dist_sq ) && dist2d_sq < min_dist_sq )
        return false;

    if ( isdefined( max_dist_sq ) && dist2d_sq > max_dist_sq )
        return false;

    if ( isdefined( max_z_delta ) && abs_z > max_z_delta )
        return false;

    // Reject steep drops from candidate seed to snapped ground (common out-of-bounds symptom).
    if ( abs( snapped[2] - origin[2] ) > 220 )
        return false;

    return true;
}

rogue_pick_safe_mech_spawn_origin(anchor)
{
    if ( !isdefined( anchor ) )
        return undefined;

    rogue_wait_for_base_spawners( 0.20 );
    zsp = rogue_pick_safe_zspawner_for_mech( anchor, 230400, 1960000, 260 ); // 480..1400 units, <=260 z delta
    if ( isdefined( zsp ) && isdefined( zsp.origin ) )
    {
        zsp_origin = rogue_ground_snap_spawn_origin( zsp.origin + ( 0, 0, 28 ) );
        if ( rogue_is_safe_mech_spawn_origin( zsp_origin, anchor, 230400, 1960000, 260 ) )
            return zsp_origin;
    }

    // Last fallback: sample in front/side arcs around player and keep only safe candidates.
    player = rogue_get_alive_player_entity();
    if ( isdefined( player ) && isdefined( player.angles ) && isdefined( player.origin ) )
    {
        forward = anglestoforward( player.angles );
        right = anglestoright( player.angles );

        for ( tries = 0; tries < 16; tries++ )
        {
            candidate = player.origin + vectorscale( forward, randomfloatrange( 520, 880 ) ) + vectorscale( right, randomfloatrange( -280, 280 ) ) + ( 0, 0, 32 );
            candidate = rogue_ground_snap_spawn_origin( candidate );
            if ( rogue_is_safe_mech_spawn_origin( candidate, anchor, 230400, 1960000, 260 ) )
                return candidate;
        }
    }

    // Absolute fallback: keep it near anchor with strict validation.
    for ( tries = 0; tries < 12; tries++ )
    {
        candidate = anchor + ( randomfloatrange( -900, 900 ), randomfloatrange( -900, 900 ), 32 );
        candidate = rogue_ground_snap_spawn_origin( candidate );
        if ( rogue_is_safe_mech_spawn_origin( candidate, anchor, 230400, 1960000, 260 ) )
            return candidate;
    }

    return undefined;
}

rogue_get_nearest_mech_location(anchor)
{
    if ( !isdefined( level.zombie_mechz_locations ) || level.zombie_mechz_locations.size < 1 )
        return undefined;

    best = undefined;
    best_dist_sq = -1;

    for ( i = 0; i < level.zombie_mechz_locations.size; i++ )
    {
        loc = level.zombie_mechz_locations[i];
        if ( !isdefined( loc ) || !isdefined( loc.origin ) )
            continue;

        if ( !isdefined( anchor ) )
            return loc;

        dx = loc.origin[0] - anchor[0];
        dy = loc.origin[1] - anchor[1];
        dz = loc.origin[2] - anchor[2];
        dist_sq = dx * dx + dy * dy + dz * dz;

        if ( !isdefined( best ) || best_dist_sq < 0 || dist_sq < best_dist_sq )
        {
            best = loc;
            best_dist_sq = dist_sq;
        }
    }

    return best;
}

rogue_make_spawn_struct(origin, source_name)
{
    if ( !isdefined( origin ) )
        return undefined;

    loc = spawnstruct();
    loc.origin = origin;
    loc.angles = ( 0, 0, 0 );
    loc.script_noteworthy = source_name;
    return loc;
}

rogue_normalize_force_spawn_origin(origin, anchor)
{
    if ( !isdefined( origin ) )
        return origin;

    if ( !rogue_is_town_variant_map() || !isdefined( anchor ) )
        return origin;

    // Keep force-spawn in the current playable area and off the player's face.
    dz = abs( origin[2] - anchor[2] );
    dx = origin[0] - anchor[0];
    dy = origin[1] - anchor[1];
    dist2d_sq = dx * dx + dy * dy;

    if ( dz > 260 || dist2d_sq < 176400 || dist2d_sq > 1960000 )
    {
        safe_origin = rogue_pick_safe_mech_spawn_origin( anchor );
        if ( isdefined( safe_origin ) )
            return safe_origin;
    }

    return origin;
}

rogue_get_force_mech_spawn_pos(anchor, fallback_origin)
{
    // Transit variants have many invalid mech locations in stock structs.
    // Prefer nearby zombie spawners for nav-safe, stable runtime spawns.
    if ( rogue_is_town_variant_map() )
    {
        if ( isdefined( anchor ) )
        {
            safe_origin = rogue_pick_safe_mech_spawn_origin( anchor );
            if ( isdefined( safe_origin ) )
                return rogue_make_spawn_struct( safe_origin, "rogue_zsp_near_player" );
        }

        // Do not fall back to unconstrained nearest zsp on Transit; it can be out-of-lane.
    }

    // Never use raw mech location structs on Transit variants; many are out-of-bounds.
    if ( !rogue_is_town_variant_map() )
    {
        loc = rogue_get_nearest_mech_location( anchor );
        if ( isdefined( loc ) && isdefined( loc.origin ) )
            return loc;
    }

    if ( isdefined( fallback_origin ) )
    {
        safe_fallback = rogue_ground_snap_spawn_origin( fallback_origin + ( 0, 0, 36 ) );
        if ( isdefined( safe_fallback ) && ( !isdefined( anchor ) || rogue_is_safe_mech_spawn_origin( safe_fallback, anchor, 160000, 2400000, 300 ) ) )
            return rogue_make_spawn_struct( safe_fallback, "rogue_fallback_origin" );
    }

    if ( isdefined( anchor ) )
    {
        safe_origin = rogue_pick_safe_mech_spawn_origin( anchor );
        if ( isdefined( safe_origin ) )
            return rogue_make_spawn_struct( safe_origin, "rogue_player_anchor" );
    }

    return undefined;
}

rogue_force_mech_spawn_near_players(round_num, reason, fallback_origin)
{
    anchor = rogue_get_alive_player_origin();
    loc = rogue_get_force_mech_spawn_pos( anchor, fallback_origin );

    if ( !isdefined( loc ) || !isdefined( loc.origin ) )
        return false;

    loc.origin = rogue_normalize_force_spawn_origin( loc.origin, anchor );
    level.mechz_force_spawn_pos = loc;
    rogue_log_event( "mech_force_spawn_pos", "round=" + round_num + ";reason=" + rogue_safe_str( reason ) + ";origin=" + rogue_safe_str( loc.origin ) + ";tn=" + rogue_safe_str( loc.targetname ) + ";sn=" + rogue_safe_str( loc.script_noteworthy ) );
    return true;
}

rogue_kill_actor_fast(ai)
{
    if ( !isdefined( ai ) || !isalive( ai ) )
        return;

    dmg = 100000;
    if ( isdefined( ai.health ) )
        dmg = ai.health + 10000;

    ai dodamage( dmg, ai.origin );
}

rogue_validate_panzer_actor_post_tune(ai, round_num, boss_type)
{
    if ( !isdefined( ai ) || !isalive( ai ) )
    {
        class_name = "<undef>";
        if ( isdefined( ai ) && isdefined( ai.classname ) )
            class_name = ai.classname;
        rogue_log_event( "spawn_reject", "round=" + round_num + ";type=" + boss_type + ";reason=dead_or_undefined_before_validate;class=" + rogue_safe_str( class_name ) );
        return false;
    }

    if ( !rogue_is_mech_actor_class( ai ) )
        return true;

    if ( !rogue_wait_for_mech_full_init( ai, 1.5 ) )
    {
        rogue_log_event( "mech_validate_force", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) + ";origin=" + rogue_safe_str( ai.origin ) );
        rogue_activate_mech_fullport( ai, round_num );

        if ( !rogue_wait_for_mech_full_init( ai, 4.5 ) )
        {
            rogue_log_event( "mech_invalid_reject", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) + ";origin=" + rogue_safe_str( ai.origin ) );
            rogue_kill_actor_fast( ai );
            return false;
        }
    }

    if ( !isdefined( ai.is_mechz ) || !ai.is_mechz || !isdefined( ai.zombie_init_done ) || !ai.zombie_init_done )
    {
        rogue_log_event( "mech_invalid_state_reject", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) + ";origin=" + rogue_safe_str( ai.origin ) );
        rogue_kill_actor_fast( ai );
        return false;
    }

    return true;
}

rogue_seed_mech_spawn_pos_from_actor(ai)
{
    if ( !isdefined( ai ) || !isdefined( ai.origin ) )
        return;

    if ( isdefined( level.zombie_mechz_locations ) && level.zombie_mechz_locations.size > 0 )
        return;

    level.zombie_mechz_locations = [];

    spawn_pos = spawnstruct();
    spawn_pos.origin = ai.origin;
    if ( isdefined( ai.angles ) )
        spawn_pos.angles = ai.angles;
    else
        spawn_pos.angles = ( 0, 0, 0 );
    spawn_pos.script_noteworthy = "rogue_mechz_fallback_spawn";

    level.zombie_mechz_locations[level.zombie_mechz_locations.size] = spawn_pos;
    rogue_log_event( "mech_seed_spawn_pos", "origin=" + rogue_safe_str( spawn_pos.origin ) );
}

rogue_activate_mech_fullport(ai, round_num)
{
    if ( !isdefined( ai ) || !isalive( ai ) )
    {
        rogue_log_event( "mech_activate_skip", "round=" + round_num + ";reason=dead_or_undefined;class=" + rogue_safe_str( ai ) );
        return;
    }

    if ( !rogue_is_mech_actor_class( ai ) )
        return;

    if ( isdefined( ai.is_mechz ) && ai.is_mechz && isdefined( ai.zombie_init_done ) && ai.zombie_init_done )
    {
        ai.ignore_enemy_count = 0;
        return;
    }

    if ( !rogue_prepare_mech_fullport_runtime() )
    {
        rogue_log_event( "mech_activate_skip", "round=" + round_num + ";reason=runtime_not_ready;class=" + rogue_safe_str( ai.classname ) );
        return;
    }

    rogue_seed_mech_spawn_pos_from_actor( ai );

    if ( !isdefined( ai.is_mechz ) || !ai.is_mechz || !isdefined( ai.zombie_init_done ) || !ai.zombie_init_done )
    {
        if ( !isdefined( ai.rogue_mech_spawn_threaded ) || !ai.rogue_mech_spawn_threaded )
        {
            ai.rogue_mech_spawn_threaded = 1;
            if ( isdefined( ai.rogue_spawn_source ) && ai.rogue_spawn_source == "utility" )
                wait 0.05;
            ai thread maps\mp\zombies\_zm_ai_mechz::mechz_spawn();
        }
    }

    tries = 0;
    while ( tries < 120 )
    {
        if ( !isdefined( ai ) || !isalive( ai ) )
            return false;
        
        if ( isdefined( ai.zombie_init_done ) && ai.zombie_init_done )
            break;

        tries++;
        wait 0.05;
    }

    if ( isdefined( round_num ) )
        ai._starting_round_number = round_num;

    ai.ignore_enemy_count = 0;
    rogue_log_event( "mech_activate_state", "round=" + round_num + ";class=" + rogue_safe_str( ai.classname ) + ";alive=" + isalive( ai ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) + ";origin=" + rogue_safe_str( ai.origin ) );
}

rogue_cleanup_orphan_mech_actors()
{
    enemies = getaispeciesarray( level.zombie_team, "all" );
    cleaned = 0;

    for ( i = 0; i < enemies.size; i++ )
    {
        ai = enemies[i];
        if ( !isdefined( ai ) || !isalive( ai ) )
            continue;

        if ( !rogue_is_mech_actor_class( ai ) )
            continue;

        if ( isdefined( ai.is_mechz ) && ai.is_mechz && isdefined( ai.zombie_init_done ) && ai.zombie_init_done )
            continue;

        rogue_kill_actor_fast( ai );
        cleaned++;
    }

    if ( cleaned > 0 )
        rogue_log_event( "mech_orphan_cleanup", "count=" + cleaned );
}

rogue_relocate_panzer_near_players(ai, round_num, boss_type)
{
    if ( !isdefined( ai ) || !isdefined( ai.origin ) )
        return;

    anchor = rogue_get_alive_player_origin();
    if ( !isdefined( anchor ) )
        return;

    dx = ai.origin[0] - anchor[0];
    dy = ai.origin[1] - anchor[1];
    dz = ai.origin[2] - anchor[2];
    dist_sq = dx * dx + dy * dy + dz * dz;

    // On Transit variants, always relocate to guarantee visual spawn near players.
    // On other maps, keep map-native spawns if already close.
    if ( !rogue_is_town_variant_map() && dist_sq <= ( 1400 * 1400 ) )
        return;

    ox = randomfloatrange( -260.0, 260.0 );
    oy = randomfloatrange( -260.0, 260.0 );
    dest = ( anchor[0] + ox, anchor[1] + oy, anchor[2] + 56.0 );
    from = ai.origin;
    ai forceteleport( dest );
    rogue_log_event( "spawn_relocate", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( ai.classname ) + ";dist_sq=" + int( dist_sq ) + ";from=" + rogue_safe_str( from ) + ";to=" + rogue_safe_str( dest ) );
}

rogue_track_panzer_lifecycle(round_num, boss_type)
{
    if ( !isdefined( self ) )
        return;

    rogue_log_event( "spawn_life_begin", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( self.classname ) + ";origin=" + rogue_safe_str( self.origin ) + ";hp=" + rogue_safe_str( self.health ) );

    wait 0.5;
    if ( !isdefined( self ) || !isalive( self ) )
        return;

    rogue_log_event( "spawn_life_0p5", "round=" + round_num + ";type=" + boss_type + ";origin=" + rogue_safe_str( self.origin ) + ";hp=" + rogue_safe_str( self.health ) );

    wait 2.5;
    if ( !isdefined( self ) || !isalive( self ) )
        return;

    rogue_log_event( "spawn_life_3p0", "round=" + round_num + ";type=" + boss_type + ";origin=" + rogue_safe_str( self.origin ) + ";hp=" + rogue_safe_str( self.health ) );
}

rogue_track_panzer_death(round_num, boss_type)
{
    if ( !isdefined( self ) )
        return;

    self waittill( "death" );
    rogue_log_event( "spawn_life_death", "round=" + round_num + ";type=" + boss_type + ";class=" + rogue_safe_str( self.classname ) + ";origin=" + rogue_safe_str( self.origin ) );
}

rogue_mech_runtime_warp_guard(round_num, boss_type)
{
    self endon( "death" );

    if ( !rogue_is_town_variant_map() )
        return;

    recoveries = 0;
    max_recoveries = 2;

    for (;;)
    {
        if ( !isdefined( self ) || !isalive( self ) )
            return;

        anchor = rogue_get_alive_player_origin();
        if ( !isdefined( anchor ) || !isdefined( self.origin ) )
        {
            wait 0.25;
            continue;
        }

        dx = self.origin[0] - anchor[0];
        dy = self.origin[1] - anchor[1];
        dz = self.origin[2] - anchor[2];
        dist2d_sq = dx * dx + dy * dy;
        abs_z = abs( dz );

        // Detect impossible relocation / out-of-lane drift and recover once or twice.
        if ( abs_z > 320 || dist2d_sq > ( 3000 * 3000 ) )
        {
            safe_origin = rogue_pick_safe_mech_spawn_origin( anchor );
            if ( isdefined( safe_origin ) )
            {
                from = self.origin;
                self forceteleport( safe_origin );
                self show();
                self solid();
                if ( isdefined( self.m_claw ) )
                    self.m_claw show();
                self.goal_pos = anchor;
                self setgoalpos( self.goal_pos );
                recoveries++;
                rogue_log_event( "mech_warp_recover", "round=" + round_num + ";type=" + boss_type + ";from=" + rogue_safe_str( from ) + ";to=" + rogue_safe_str( safe_origin ) + ";dz=" + int( abs_z ) + ";d2d=" + int( sqrt( dist2d_sq ) ) + ";recoveries=" + recoveries );
            }
        }

        if ( recoveries >= max_recoveries )
            return;

        wait 0.25;
    }
}

rogue_try_spawn_mech_via_utility(spawner, round_num)
{
    if ( !isdefined( spawner ) )
        return undefined;

    target = "";
    spawn_point = undefined;
    if ( isdefined( spawner.targetname ) )
        target = spawner.targetname;

    if ( target == "" && isdefined( level.zombie_mechz_locations ) && level.zombie_mechz_locations.size > 0 )
    {
        loc = level.zombie_mechz_locations[randomint( level.zombie_mechz_locations.size )];
        if ( isdefined( loc ) )
        {
            spawn_point = loc;
            if ( isdefined( loc.targetname ) )
                target = loc.targetname;
        }
    }

    // Mirrors Origins mech setup before calling _zm_utility::spawn_zombie().
    spawner.is_enabled = 1;
    spawner.script_forcespawn = 1;

    level.rogue_last_panzer_spawn_path = "utility";
    rogue_log_event( "utility_try_begin", "round=" + round_num + ";tn=" + target + ";sn=" + rogue_safe_str( spawner.script_noteworthy ) + ";class=" + rogue_safe_str( spawner.classname ) + ";sf=" + rogue_safe_str( spawner.script_forcespawn ) + ";ie=" + rogue_safe_str( spawner.is_enabled ) );

    ai = maps\mp\zombies\_zm_utility::spawn_zombie( spawner, target, spawn_point, round_num );

    if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
    {
        ai.rogue_is_panzer = 1;
        ai.rogue_panzer_type = "mechz";
        ai.rogue_spawn_grace_until = gettime() + 5000;
        ai.rogue_spawn_source = "utility";
        ai.rogue_needs_mech_activation = 1;
        level.rogue_last_panzer_spawn_path = "utility:ok";
        return ai;
    }

    if ( isdefined( ai ) && isalive( ai ) )
    {
        rogue_log_event( "utility_try_nonmech", "round=" + round_num + ";variant=single;class=" + rogue_safe_str( ai.classname ) );
        ai dodamage( ai.health + 10000, ai.origin );
    }

    if ( isdefined( spawner.origin ) )
    {
        ai = rogue_spawn_direct_mech_actor( spawner.origin, round_num );
        if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
        {
            level.rogue_last_panzer_spawn_path = "utility:direct";
            return ai;
        }
    }

    level.rogue_last_panzer_spawn_path = "utility:all_failed";
    rogue_log_event( "utility_all_failed", "round=" + round_num + ";tn=" + target + ";class=" + rogue_safe_str( spawner.classname ) + ";sn=" + rogue_safe_str( spawner.script_noteworthy ) );
    return undefined;
}

rogue_is_origins_map()
{
    map_name = tolower( getdvar( "mapname" ) );

    if ( !isdefined( map_name ) || map_name == "" )
        return false;

    return map_name == "zm_tomb";
}

rogue_prepare_mechz_runtime()
{
    // Seed mechz locations from explicit markers first, then fall back to stock map spawn points.
    if ( isdefined( level.zombie_mechz_locations ) && level.zombie_mechz_locations.size > 0 )
    {
        rogue_prepare_mechz_spawners();
        return;
    }

    level.zombie_mechz_locations = [];
    rogue_append_structs_by_noteworthy( "mechz_location" );

    if ( level.zombie_mechz_locations.size < 1 )
        rogue_append_structs_by_noteworthy( "zombie_location" );

    if ( level.zombie_mechz_locations.size < 1 )
        rogue_append_structs_by_noteworthy( "spawn_location" );

    if ( level.zombie_mechz_locations.size < 1 )
        rogue_append_structs_by_noteworthy( "riser_location" );

    rogue_prepare_mechz_spawners();

    loc_count = 0;
    spawner_count = 0;
    if ( isdefined( level.zombie_mechz_locations ) )
        loc_count = level.zombie_mechz_locations.size;
    if ( isdefined( level.mechz_spawners ) )
        spawner_count = level.mechz_spawners.size;
    rogue_log_event( "mech_runtime_prepare", "locations=" + loc_count + ";mech_spawners=" + spawner_count );
}

rogue_prepare_mechz_spawners()
{
    if ( !isdefined( level.mechz_spawners ) || level.mechz_spawners.size < 1 )
        level.mechz_spawners = rogue_get_mechz_spawners();

    if ( !isdefined( level.mechz_spawners ) || level.mechz_spawners.size < 1 )
        return;

    for ( i = 0; i < level.mechz_spawners.size; i++ )
    {
        s = level.mechz_spawners[i];
        if ( !isdefined( s ) )
            continue;

        s.is_enabled = 1;
        s.script_forcespawn = 1;
    }
}

rogue_append_structs_by_noteworthy(noteworthy)
{
    locs = getstructarray( noteworthy, "script_noteworthy" );

    for ( i = 0; i < locs.size; i++ )
    {
        if ( !isdefined( locs[i] ) )
            continue;

        level.zombie_mechz_locations[level.zombie_mechz_locations.size] = locs[i];
    }
}

rogue_get_mechz_spawners()
{
    spawners = getentarray( "mechz_spawner", "script_noteworthy" );

    return spawners;
}

rogue_array_has_entity(arr, ent)
{
    if ( !isdefined( arr ) || !isdefined( ent ) )
        return false;

    for ( i = 0; i < arr.size; i++ )
    {
        if ( !isdefined( arr[i] ) )
            continue;

        if ( arr[i] == ent )
            return true;
    }

    return false;
}

rogue_mechz_spawning_logic_override()
{
    level endon( "intermission" );

    for (;;)
        wait 5.0;
}

rogue_ensure_mech_flamethrower_triggers()
{
    existing = getentarray( "flamethrower_trigger", "script_noteworthy" );
    if ( existing.size >= 4 )
        return;

    // _zm_ai_mechz_ft::init_flamethrower_triggers() asserts on <4 entries.
    // Provide inert fallback trigger_radius ents for non-Origins maps.
    for ( i = existing.size; i < 4; i++ )
    {
        trig = spawn( "trigger_radius", ( 0, 0, -50000 - ( i * 32 ) ), 0, 16, 64 );
        if ( !isdefined( trig ) )
            continue;

        trig.script_noteworthy = "flamethrower_trigger";
        trig.in_use = 0;
    }
}

rogue_prepare_mech_fullport_runtime()
{
    if ( isdefined( level.rogue_mech_fullport_ready ) && level.rogue_mech_fullport_ready )
        return true;

    if ( isdefined( level.rogue_mech_fullport_failed ) && level.rogue_mech_fullport_failed )
        return false;

    level.mechz_spawning_logic_override_func = ::rogue_mechz_spawning_logic_override;
    rogue_ensure_mech_flamethrower_triggers();
    maps\mp\zombies\_zm_ai_mechz::precache();
    maps\mp\zombies\_zm_ai_mechz::init();
    wait 0.20;
    level.rogue_mech_fullport_ready = 1;
    return true;
}

rogue_wait_for_mech_full_init(ai, timeout_sec)
{
    if ( !isdefined( ai ) || !isalive( ai ) )
        return false;

    if ( !rogue_is_mech_actor_class( ai ) )
        return true;

    if ( !isdefined( timeout_sec ) || timeout_sec < 0.2 )
        timeout_sec = 5.0;

    end_time = gettime() + int( timeout_sec * 1000.0 );

    for (;;)
    {
        if ( !isdefined( ai ) || !isalive( ai ) )
            return false;

        if ( isdefined( ai.is_mechz ) && ai.is_mechz )
            return true;

        if ( isdefined( ai.zombie_init_done ) && ai.zombie_init_done )
            return true;

        if ( gettime() >= end_time )
            break;

        wait 0.05;
    }

    return false;
}

rogue_init_mechz_runtime_for_all_maps()
{
    if ( isdefined( level.rogue_mechz_runtime_ready ) && level.rogue_mechz_runtime_ready )
        return true;

    if ( isdefined( level.rogue_mechz_runtime_failed ) && level.rogue_mechz_runtime_failed )
        return false;

    level.rogue_mechz_runtime_fail_reason = "";
    rogue_prepare_mechz_runtime();
    rogue_prepare_mech_fullport_runtime();

    if ( !isdefined( level.zombie_mechz_locations ) || level.zombie_mechz_locations.size < 1 )
    {
        level.rogue_mechz_runtime_fail_reason = "no mechz/zombie spawn locations";
        level.rogue_mechz_runtime_failed = 1;
        return false;
    }

    wait 0.10;

    if ( !isdefined( level.mechz_spawners ) || level.mechz_spawners.size < 1 )
        level.mechz_spawners = rogue_get_mechz_spawners();

    if ( !isdefined( level.mechz_spawners ) || level.mechz_spawners.size < 1 )
    {
        level.rogue_mechz_runtime_fail_reason = "no mechz spawners in map ents";
        level.rogue_mechz_runtime_failed = 1;
        return false;
    }

    level.rogue_mechz_runtime_ready = 1;
    level.rogue_mechz_runtime_failed = 0;
    level.rogue_mechz_runtime_fail_reason = "";
    return true;
}

rogue_get_alive_mechz_count()
{
    count = 0;
    zombies = getaispeciesarray( level.zombie_team, "all" );

    for ( i = 0; i < zombies.size; i++ )
    {
        ai = zombies[i];

        if ( isdefined( ai ) && isalive( ai ) && isdefined( ai.is_mechz ) && ai.is_mechz )
            count++;
    }

    return count;
}

rogue_tune_panzer_actor(ai, round_num, type)
{
    if ( !isdefined( ai ) )
        return;

    if ( rogue_is_mech_actor_class( ai ) )
    {
        needs_activation = 0;
        if ( isdefined( ai.rogue_needs_mech_activation ) && ai.rogue_needs_mech_activation )
            needs_activation = 1;

        if ( isdefined( ai.rogue_spawn_source ) && ai.rogue_spawn_source == "utility" )
        {
            // Utility spawns frequently return a cold actor_zm_tomb_mech_zombie shell.
            // Force full mech init before any panzer tuning/counting.
            if ( !isdefined( ai.is_mechz ) && !isdefined( ai.zombie_init_done ) )
            {
                needs_activation = 1;
                rogue_log_event( "mech_activate_force_utility", "round=" + round_num + ";src=utility;class=" + rogue_safe_str( ai.classname ) + ";origin=" + rogue_safe_str( ai.origin ) );
            }
            else
            {
                needs_activation = 0;
                rogue_log_event( "mech_activate_skip_ok", "round=" + round_num + ";src=utility;is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) );
            }
        }
        else if ( !isdefined( ai.is_mechz ) || !ai.is_mechz || !isdefined( ai.zombie_init_done ) || !ai.zombie_init_done )
            needs_activation = 1;

        if ( needs_activation )
        {
            rogue_log_event( "mech_activate_force", "round=" + round_num + ";src=" + rogue_safe_str( ai.rogue_spawn_source ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) );
            rogue_activate_mech_fullport( ai, round_num );
            if ( !rogue_wait_for_mech_full_init( ai, 4.5 ) )
            {
                rogue_log_event( "mech_tune_init_fail", "round=" + round_num + ";type=" + rogue_safe_str( type ) + ";src=" + rogue_safe_str( ai.rogue_spawn_source ) + ";class=" + rogue_safe_str( ai.classname ) + ";origin=" + rogue_safe_str( ai.origin ) );
                rogue_kill_actor_fast( ai );
                return;
            }
        }
        else if ( !( isdefined( ai.rogue_spawn_source ) && ai.rogue_spawn_source == "utility" ) )
            rogue_log_event( "mech_activate_skip_ok", "round=" + round_num + ";src=" + rogue_safe_str( ai.rogue_spawn_source ) + ";is_mechz=" + rogue_safe_str( ai.is_mechz ) + ";init_done=" + rogue_safe_str( ai.zombie_init_done ) );
    }

    round_mult = rogue_get_round_multiplier( round_num );
    base_hp = 9000;
    base_melee = 50;

    if ( isdefined( type ) && type == "mechz" )
    {
        base_hp = 14000;
        base_melee = 70;
    }
    else if ( isdefined( type ) && ( type == "brutus" || type == "sloth" ) )
    {
        base_hp = 12000;
        base_melee = 62;
    }
    else if ( isdefined( type ) && ( type == "avogadro" || type == "screecher" || type == "leaper" ) )
    {
        base_hp = 10500;
        base_melee = 56;
    }
    else if ( isdefined( type ) && type == "proxy_panzer" )
    {
        base_hp = 9500;
        base_melee = 54;
    }

    scaled_hp = int( base_hp * round_mult * randomfloatrange( 0.92, 1.18 ) );

    if ( scaled_hp < 3500 )
        scaled_hp = 3500;

    ai.maxhealth = scaled_hp;
    ai.health = ai.maxhealth;
    ai.rogue_boss_class = type;
    ai.rogue_enrage_stacks = 0;
    ai.rogue_boss_round = round_num;

    if ( isdefined( ai.meleedamage ) )
        ai.meleedamage = base_melee + int( round_num * 3 );

    // Must be counted by round logic; otherwise rounds insta-end.
    ai.ignore_enemy_count = 0;

    if ( rogue_is_mech_actor_class( ai ) || ( isdefined( type ) && type == "mechz" ) )
    {
        rogue_log_event( "mech_native_ai_mode", "round=" + round_num + ";type=" + rogue_safe_str( type ) + ";class=" + rogue_safe_str( ai.classname ) );
        return;
    }

    ai thread rogue_boss_regen_think();
    ai thread rogue_boss_jump_think();
    ai thread rogue_boss_enrage_think();
}

rogue_debug_panzer(text)
{
    rogue_log_event( "panzer_dbg", text );

    if ( getdvarint( "rogue_panzer_debug" ) != 1 )
        return;

    rogue_broadcast( "^5[panzer dbg]^7 " + text );
}

rogue_log_event(event_name, msg)
{
    map_name = tolower( getdvar( "mapname" ) );
    if ( !isdefined( map_name ) || map_name == "" )
        map_name = "unknown";

    if ( !isdefined( event_name ) || event_name == "" )
        event_name = "event";

    if ( !isdefined( msg ) )
        msg = "";

    line = "[ROGUE] event=" + event_name + ";map=" + map_name + ";msg=" + msg;
    logprint( line + "\n" );

    // Some Pluto builds don't flush games_mp.log reliably mid-match.
    // Always mirror to server console so failures are visible in console_zm.log.
    println( line );
}

rogue_safe_str(v)
{
    if ( !isdefined( v ) )
        return "<undef>";

    return "" + v;
}

rogue_join_weapons_compact(weapons, max_items)
{
    if ( !isdefined( weapons ) || !isarray( weapons ) )
        return "[]";

    cap = weapons.size;
    if ( !isdefined( max_items ) || max_items < 1 )
        max_items = 8;
    if ( cap > max_items )
        cap = max_items;

    out = "";
    for ( i = 0; i < cap; i++ )
    {
        if ( i > 0 )
            out += ",";
        out += rogue_safe_str( weapons[i] );
    }

    if ( weapons.size > cap )
        out += ",+more(" + ( weapons.size - cap ) + ")";

    return "[" + out + "]";
}

rogue_tg_log_player_state(player, stage, weapon_name)
{
    if ( !isdefined( player ) || !isplayer( player ) )
    {
        rogue_log_event( "tg_state", "stage=" + rogue_safe_str( stage ) + ";wpn=" + rogue_safe_str( weapon_name ) + ";player=<invalid>" );
        return;
    }

    cur = player getcurrentweapon();
    if ( !isdefined( cur ) )
        cur = "<undef>";

    inv = player getweaponslist( 1 );
    inv_count = 0;
    if ( isdefined( inv ) && isarray( inv ) )
        inv_count = inv.size;

    msg = "stage=" + rogue_safe_str( stage ) + ";wpn=" + rogue_safe_str( weapon_name ) + ";cur=" + rogue_safe_str( cur ) + ";inv_count=" + inv_count + ";inv=" + rogue_join_weapons_compact( inv, 10 );
    rogue_log_event( "tg_state", msg );
}

rogue_is_mech_actor_class(ai)
{
    if ( !isdefined( ai ) || !isdefined( ai.classname ) )
        return false;

    name = tolower( ai.classname );
    return issubstr( name, "mech" );
}

rogue_get_alive_players()
{
    alive = [];
    players = getplayers();

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isalive( players[i] ) )
            continue;

        alive[alive.size] = players[i];
    }

    return alive;
}

rogue_pick_boss_target()
{
    alive = rogue_get_alive_players();

    if ( alive.size < 1 )
        return undefined;

    return alive[randomint( alive.size )];
}

rogue_boss_regen_think()
{
    self endon( "death" );

    for (;;)
    {
        wait randomfloatrange( 3.6, 5.8 );

        if ( !isdefined( self ) || !isalive( self ) )
            break;

        if ( !isdefined( self.maxhealth ) || self.maxhealth <= 1 )
            continue;

        if ( !isdefined( self.health ) || self.health >= self.maxhealth )
            continue;

        heal = int( self.maxhealth * 0.05 );
        self.health = self.health + heal;

        if ( self.health > self.maxhealth )
            self.health = self.maxhealth;
    }
}

rogue_boss_jump_think()
{
    if ( rogue_is_mech_actor_class( self ) )
        return;

    self endon( "death" );

    for (;;)
    {
        wait randomfloatrange( 6.0, 9.2 );

        if ( !isdefined( self ) || !isalive( self ) )
            break;

        target = rogue_pick_boss_target();

        if ( !isdefined( target ) || !isalive( target ) )
            continue;

        if ( distance2dsquared( self.origin, target.origin ) < 90000 )
            continue;

        jump_pos = target.origin + ( randomfloatrange( -90, 90 ), randomfloatrange( -90, 90 ), 0 );
        self forceteleport( jump_pos );
    }
}

rogue_boss_enrage_think()
{
    self endon( "death" );

    for (;;)
    {
        wait randomfloatrange( 7.5, 11.0 );

        if ( !isdefined( self ) || !isalive( self ) )
            break;

        self.rogue_enrage_stacks++;

        if ( isdefined( self.meleedamage ) )
            self.meleedamage = self.meleedamage + 4;

        if ( isdefined( self.maxhealth ) && self.maxhealth > 0 )
        {
            bonus_hp = int( self.maxhealth * 0.02 );
            self.health = self.health + bonus_hp;

            if ( self.health > self.maxhealth )
                self.health = self.maxhealth;
        }
    }
}

rogue_panzer_spawn_lockdown()
{
    while ( isdefined( level.rogue_started ) && level.rogue_started && isdefined( level.rogue_panzer_mode ) && level.rogue_panzer_mode )
    {
        common_scripts\utility::flag_clear( "spawn_zombies" );

        if ( isdefined( level.zombie_total ) && level.zombie_total > 0 )
            level.zombie_total = 0;

        if ( !isdefined( level.rogue_wave_spawning ) || !level.rogue_wave_spawning )
            rogue_kill_non_panzer_enemies();
        wait 0.15;
    }
}

rogue_kill_non_panzer_enemies()
{
    enemies = getaispeciesarray( level.zombie_team, "all" );
    now_ms = gettime();

    for ( i = 0; i < enemies.size; i++ )
    {
        ai = enemies[i];

        if ( !isdefined( ai ) || !isalive( ai ) )
            continue;

        if ( rogue_is_panzer_actor( ai ) )
            continue;

        if ( rogue_is_mech_actor_class( ai ) )
            continue;

        ai dodamage( ai.health + 10000, ai.origin );
    }
}

rogue_is_panzer_actor(ai)
{
    if ( !isdefined( ai ) )
        return false;

    if ( isdefined( ai.rogue_is_panzer ) && ai.rogue_is_panzer )
        return true;

    if ( isdefined( ai.is_mechz ) && ai.is_mechz )
        return true;

    if ( isdefined( ai.is_brutus ) && ai.is_brutus )
        return true;

    if ( isdefined( ai.is_sloth ) && ai.is_sloth )
        return true;

    if ( isdefined( ai.is_avogadro ) && ai.is_avogadro )
        return true;

    if ( isdefined( ai.is_screecher ) && ai.is_screecher )
        return true;

    if ( isdefined( ai.is_leaper ) && ai.is_leaper )
        return true;

    if ( isdefined( ai.targetname ) )
    {
        if ( issubstr( ai.targetname, "mechz" ) || issubstr( ai.targetname, "brutus" ) || issubstr( ai.targetname, "sloth" ) || issubstr( ai.targetname, "avogadro" ) || issubstr( ai.targetname, "screecher" ) || issubstr( ai.targetname, "leaper" ) )
            return true;
    }

    return false;
}

rogue_wait_for_panzer_wave_clear(spawned, round_num)
{
    if ( !isdefined( spawned ) )
        return;

    end_time = gettime() + 900000; // 15 minute safety timeout.
    recover_deadline = gettime() + 9000;
    recover_attempts = 0;

    for (;;)
    {
        alive_count = 0;

        for ( i = 0; i < spawned.size; i++ )
        {
            if ( isdefined( spawned[i] ) && isalive( spawned[i] ) )
                alive_count++;
        }

        if ( alive_count < 1 )
            alive_count = rogue_count_alive_round_bosses( round_num );

        if ( alive_count < 1 )
        {
            if ( gettime() < recover_deadline && recover_attempts < 3 )
            {
                replacement = rogue_try_recover_panzer_for_round( round_num );
                recover_attempts++;

                if ( isdefined( replacement ) && isalive( replacement ) )
                {
                    spawned[spawned.size] = replacement;
                    rogue_log_event( "wave_recover_ok", "round=" + round_num + ";attempt=" + recover_attempts + ";class=" + rogue_safe_str( replacement.classname ) );
                    wait 0.20;
                    continue;
                }

                rogue_log_event( "wave_recover_fail", "round=" + round_num + ";attempt=" + recover_attempts );
                wait 0.20;
                continue;
            }

            break;
        }

        if ( gettime() >= end_time )
            break;

        wait 0.20;
    }

    rogue_broadcast( "^2Round " + round_num + " clear.^7 Prepare your boon." );
}

rogue_try_recover_panzer_for_round(round_num)
{
    spawn_origin = rogue_get_alive_player_origin();
    if ( !isdefined( spawn_origin ) )
        spawn_origin = rogue_get_spawn_center_origin();

    ai = undefined;
    if ( isdefined( spawn_origin ) )
        ai = rogue_spawn_direct_mech_actor( spawn_origin, round_num );

    if ( !isdefined( ai ) || !isalive( ai ) || !rogue_is_mech_actor_class( ai ) )
    {
        if ( isdefined( spawn_origin ) )
            ai = rogue_spawn_proxy_mech_actor( spawn_origin, round_num );
    }

    if ( !isdefined( ai ) || !isalive( ai ) || !rogue_is_mech_actor_class( ai ) )
    {
        pool = rogue_get_panzer_spawner_pool();
        for ( i = 0; i < pool.size; i++ )
        {
            if ( !isdefined( pool[i] ) || !isdefined( pool[i].spawner ) )
                continue;

            if ( pool[i].type == "mechz_direct_point" )
                ai = rogue_spawn_direct_mech_actor( pool[i].spawner.origin, round_num );
            else
                ai = rogue_try_spawn_mech_via_utility( pool[i].spawner, round_num );

            if ( isdefined( ai ) && isalive( ai ) && rogue_is_mech_actor_class( ai ) )
                break;
        }
    }

    if ( !isdefined( ai ) || !isalive( ai ) || !rogue_is_mech_actor_class( ai ) )
        return undefined;

    ai.rogue_is_panzer = 1;
    ai.rogue_panzer_type = "mechz";
    ai.rogue_round_spawned = round_num;
    rogue_force_mech_spawn_near_players( round_num, "recover", spawn_origin );
    rogue_tune_panzer_actor( ai, round_num, "mechz" );

    if ( !rogue_validate_panzer_actor_post_tune( ai, round_num, "mechz_recover" ) )
        return undefined;

    ai thread rogue_track_panzer_lifecycle( round_num, "mechz_recover" );
    ai thread rogue_track_panzer_death( round_num, "mechz_recover" );
    return ai;
}

rogue_count_alive_round_bosses(round_num)
{
    count = 0;
    enemies = getaispeciesarray( level.zombie_team, "all" );

    for ( i = 0; i < enemies.size; i++ )
    {
        ai = enemies[i];

        if ( !isdefined( ai ) || !isalive( ai ) )
            continue;

        if ( !rogue_is_panzer_actor( ai ) )
            continue;

        if ( isdefined( ai.rogue_round_spawned ) && ai.rogue_round_spawned == round_num )
            count++;
    }

    return count;
}

rogue_player_pick_boon(cleared_round)
{
    self endon( "disconnect" );

    options = rogue_pick_boon_options( 3 );

    if ( options.size < 1 )
    {
        self.rogue_boon_pick_done_round = cleared_round;
        return;
    }

    selected = 0;
    menu = self create_rogue_boon_hud();
    self update_rogue_boon_hud( menu, options, selected, cleared_round );
    start_time = gettime();
    timeout_ms = 20000;

    for (;;)
    {
        if ( !isalive( self ) )
            break;

        if ( self attackbuttonpressed() )
        {
            selected++;

            if ( selected >= options.size )
                selected = 0;

            self wait_attack_release();
            self update_rogue_boon_hud( menu, options, selected, cleared_round );
            continue;
        }

        if ( self adsbuttonpressed() )
        {
            selected--;

            if ( selected < 0 )
                selected = options.size - 1;

            self wait_ads_release();
            self update_rogue_boon_hud( menu, options, selected, cleared_round );
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

    self destroy_rogue_boon_hud( menu );

    if ( selected < 0 || selected >= options.size )
        selected = 0;

    self rogue_apply_selected_boon( options[selected] );
    self iprintlnbold( "^2Zombie Chicken Chit:^7 " + options[selected].name );
    self.rogue_boon_pick_done_round = cleared_round;
}

create_rogue_boon_hud()
{
    menu = spawnstruct();
    menu.all_elems = [];
    s = get_picker_text_scale();

    menu.box = self create_picker_shader_elem( undefined, "CENTER", "CENTER", 0, 0, 760, 250, ( 0.06, 0.08, 0.14 ), 0.90, 40 );
    menu.head = self create_picker_shader_elem( menu.box, "TOP", "TOP", 0, 20, 724, 38, ( 0.14, 0.22, 0.32 ), 0.95, 41 );
    menu.title = self create_picker_text_elem( menu.box, "TOP", "TOP", 0, 6, "objective", s + 0.02, ( 1.00, 0.82, 0.36 ), 42 );
    menu.sub = self create_picker_text_elem( menu.box, "TOP", "TOP", 0, 30, "objective", s, ( 0.90, 0.90, 0.90 ), 42 );

    menu.opt_0 = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 26, 72, "objective", s, ( 0.70, 0.88, 1.00 ), 42 );
    menu.opt_1 = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 26, 108, "objective", s, ( 0.70, 0.88, 1.00 ), 42 );
    menu.opt_2 = self create_picker_text_elem( menu.box, "TOPLEFT", "TOPLEFT", 26, 144, "objective", s, ( 0.70, 0.88, 1.00 ), 42 );

    menu.desc = self create_picker_text_elem( menu.box, "BOTTOMLEFT", "BOTTOMLEFT", 26, -34, "objective", s, ( 1.00, 0.70, 0.70 ), 42 );
    menu.help = self create_picker_text_elem( menu.box, "BOTTOM", "BOTTOM", 0, -12, "objective", s, ( 0.90, 0.90, 0.90 ), 42 );

    menu.all_elems[menu.all_elems.size] = menu.box;
    menu.all_elems[menu.all_elems.size] = menu.head;
    menu.all_elems[menu.all_elems.size] = menu.title;
    menu.all_elems[menu.all_elems.size] = menu.sub;
    menu.all_elems[menu.all_elems.size] = menu.opt_0;
    menu.all_elems[menu.all_elems.size] = menu.opt_1;
    menu.all_elems[menu.all_elems.size] = menu.opt_2;
    menu.all_elems[menu.all_elems.size] = menu.desc;
    menu.all_elems[menu.all_elems.size] = menu.help;
    return menu;
}

update_rogue_boon_hud(menu, options, selected, cleared_round)
{
    if ( !isdefined( menu ) || !isdefined( options ) || options.size < 1 )
        return;

    line_0 = "  " + fit_label( options[0].name, 64 );
    line_1 = "  " + fit_label( options[1].name, 64 );
    line_2 = "  " + fit_label( options[2].name, 64 );

    if ( selected == 0 )
        line_0 = "^2>^7 " + fit_label( options[0].name, 64 );

    if ( selected == 1 )
        line_1 = "^2>^7 " + fit_label( options[1].name, 64 );

    if ( selected == 2 )
        line_2 = "^2>^7 " + fit_label( options[2].name, 64 );

    menu.title settext( "ZOMBIE CHICKEN CHITS" );
    menu.sub settext( "Round " + cleared_round + " clear - choose one boon" );
    menu.opt_0 settext( line_0 );
    menu.opt_1 settext( line_1 );
    menu.opt_2 settext( line_2 );
    menu.desc settext( fit_label( options[selected].desc, 78 ) );
    menu.help settext( "ADS: prev  ATTACK: next  USE: select" );
}

destroy_rogue_boon_hud(menu)
{
    if ( !isdefined( menu ) || !isdefined( menu.all_elems ) )
        return;

    for ( i = 0; i < menu.all_elems.size; i++ )
    {
        if ( isdefined( menu.all_elems[i] ) )
            menu.all_elems[i] destroy();
    }
}

rogue_pick_boon_options(count)
{
    catalog = rogue_build_boon_catalog();
    picks = [];
    used = [];

    if ( !isdefined( catalog ) || catalog.size == 0 )
        return picks;

    attempts = 0;
    while ( picks.size < count && attempts < 300 )
    {
        attempts++;
        idx = randomint( catalog.size );

        if ( array_contains( used, idx ) )
            continue;

        used[used.size] = idx;
        picks[picks.size] = catalog[idx];
    }

    while ( picks.size < count )
        picks[picks.size] = catalog[picks.size % catalog.size];

    return picks;
}

rogue_build_boon_catalog()
{
    if ( isdefined( level.rogue_boon_catalog ) && level.rogue_boon_catalog.size > 0 )
        return level.rogue_boon_catalog;

    catalog = [];
    catalog[catalog.size] = rogue_make_boon( "titan_heart", "Hammer of Titans", "+35 max health and full heal." );
    catalog[catalog.size] = rogue_make_boon( "swift_steps", "Hammer of Haste", "+6% movement speed." );
    catalog[catalog.size] = rogue_make_boon( "war_chest", "Hammer of Wealth", "+1500 now and +500 each round." );
    catalog[catalog.size] = rogue_make_boon( "ammo_printer", "Hammer of Ammunition", "Refill ammo now and at each round start." );
    catalog[catalog.size] = rogue_make_boon( "perk_infusion", "Hammer of Infusion", "Gain one perk now and one random perk each round." );
    catalog[catalog.size] = rogue_make_boon( "arsenal_drop", "Hammer of Arsenal", "Gain one random bonus weapon." );
    catalog[catalog.size] = rogue_make_boon( "jug_forge", "Hammer of Juggernaut", "Guarantee Juggernog and +20 max health." );
    catalog[catalog.size] = rogue_make_boon( "melee_mastery", "Hammer of Knuckles", "Upgrade melee and gain +10 max health." );
    catalog[catalog.size] = rogue_make_boon( "scavenger_core", "Hammer of Scavenger", "+300 round income and ammo printer." );
    catalog[catalog.size] = rogue_make_boon( "phoenix_skin", "Hammer of Phoenix", "+25 max health and +750 points." );
    catalog[catalog.size] = rogue_make_boon( "mystery_spark", "Hammer of Chaos", "Randomly triggers another boon effect." );
    catalog[catalog.size] = rogue_make_boon( "wunder_pull", "Hammer of Wonder", "High chance to gain a wonder weapon." );
    level.rogue_boon_catalog = catalog;
    return level.rogue_boon_catalog;
}

rogue_make_boon(id, name, desc)
{
    b = spawnstruct();
    b.id = id;
    b.name = name;
    b.desc = desc;
    return b;
}

rogue_apply_selected_boon(boon)
{
    if ( !isdefined( boon ) || !isdefined( boon.id ) )
        return;

    if ( !isdefined( self.rogue_bonus_health ) )
        self.rogue_bonus_health = 0;

    if ( !isdefined( self.rogue_move_speed_bonus ) )
        self.rogue_move_speed_bonus = 0;

    if ( !isdefined( self.rogue_round_points_bonus ) )
        self.rogue_round_points_bonus = 0;

    if ( !isdefined( self.rogue_round_perk_rolls ) )
        self.rogue_round_perk_rolls = 0;

    if ( !isdefined( self.rogue_round_ammo_refill ) )
        self.rogue_round_ammo_refill = 0;

    switch ( boon.id )
    {
        case "titan_heart":
            self.rogue_bonus_health += 35;
            self.health = self.maxhealth;
            break;
        case "swift_steps":
            self.rogue_move_speed_bonus += 0.06;
            break;
        case "war_chest":
            self.score += 1500;
            self.rogue_round_points_bonus += 500;
            break;
        case "ammo_printer":
            self.rogue_round_ammo_refill = 1;
            self rogue_refill_all_weapons();
            break;
        case "perk_infusion":
            self.rogue_round_perk_rolls++;
            self rogue_give_random_missing_perk();
            break;
        case "arsenal_drop":
            self rogue_give_random_bonus_weapon();
            break;
        case "jug_forge":
            if ( !self hasperk( "specialty_armorvest" ) )
                self maps\mp\zombies\_zm_perks::give_perk( "specialty_armorvest", 0 );

            self.rogue_bonus_health += 20;
            break;
        case "melee_mastery":
            self give_selected_melee( "tazer_knuckles_zm" );
            self.rogue_bonus_health += 10;
            break;
        case "scavenger_core":
            self.rogue_round_points_bonus += 300;
            self.rogue_round_ammo_refill = 1;
            break;
        case "phoenix_skin":
            self.rogue_bonus_health += 25;
            self.score += 750;
            break;
        case "wunder_pull":
            self rogue_give_random_bonus_weapon();
            self rogue_give_random_bonus_weapon();
            break;
        case "mystery_spark":
            roll = randomint( 4 );

            if ( roll == 0 )
                self.rogue_bonus_health += 20;
            else if ( roll == 1 )
                self.rogue_round_points_bonus += 400;
            else if ( roll == 2 )
                self.rogue_round_perk_rolls++;
            else
                self.rogue_round_ammo_refill = 1;
            break;
        default:
            break;
    }

    self rogue_apply_persistent_boon_effects();
}

rogue_give_random_missing_perk()
{
    pool = build_perk_pool();
    candidates = [];

    for ( i = 0; i < pool.size; i++ )
    {
        if ( self hasperk( pool[i] ) )
            continue;

        candidates[candidates.size] = pool[i];
    }

    if ( candidates.size < 1 )
        return;

    pick = candidates[randomint( candidates.size )];
    self maps\mp\zombies\_zm_perks::give_perk( pick, 0 );
}

rogue_give_random_bonus_weapon()
{
    weapon_pool = build_weapon_pool();

    if ( weapon_pool.size < 1 )
        return;

    attempts = 0;
    while ( attempts < 120 )
    {
        attempts++;
        weapon = weapon_pool[randomint( weapon_pool.size )];

        if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
            continue;

        if ( self hasweapon( weapon ) )
            continue;

        if ( self try_give_loadout_weapon( weapon ) )
            return;
    }
}

rogue_refill_all_weapons()
{
    all_weapons = self getweaponslist( 1 );

    for ( i = 0; i < all_weapons.size; i++ )
        self give_max_ammo( all_weapons[i] );
}

rogue_apply_round_start_boons()
{
    if ( isdefined( self.rogue_round_points_bonus ) && self.rogue_round_points_bonus > 0 )
        self.score += self.rogue_round_points_bonus;

    if ( isdefined( self.rogue_round_ammo_refill ) && self.rogue_round_ammo_refill )
        self rogue_refill_all_weapons();

    if ( isdefined( self.rogue_round_perk_rolls ) && self.rogue_round_perk_rolls > 0 )
    {
        rolls = self.rogue_round_perk_rolls;

        if ( rolls > 3 )
            rolls = 3;

        for ( i = 0; i < rolls; i++ )
            self rogue_give_random_missing_perk();
    }

    self rogue_apply_persistent_boon_effects();
}

rogue_apply_persistent_boon_effects()
{
    if ( !is_zombies_map() )
        return;

    if ( !isdefined( self.rogue_bonus_health ) )
        self.rogue_bonus_health = 0;

    if ( !isdefined( self.rogue_move_speed_bonus ) )
        self.rogue_move_speed_bonus = 0;

    if ( !isdefined( self.rogue_round_points_bonus ) )
        self.rogue_round_points_bonus = 0;

    if ( !isdefined( self.rogue_round_perk_rolls ) )
        self.rogue_round_perk_rolls = 0;

    max_hp = 100 + self.rogue_bonus_health;

    if ( max_hp > 325 )
        max_hp = 325;

    if ( isalive( self ) )
    {
        self.maxhealth = max_hp;

        if ( !isdefined( self.rogue_health_synced ) || !self.rogue_health_synced || self.health > self.maxhealth )
            self.health = self.maxhealth;

        self.rogue_health_synced = 1;
    }

    speed = 1.0 + self.rogue_move_speed_bonus;

    if ( speed < 0.90 )
        speed = 0.90;

    if ( speed > 1.35 )
        speed = 1.35;

    self setmovespeedscale( speed );
}

rogue_get_round_multiplier(round_num)
{
    if ( round_num < 1 )
        round_num = 1;

    mult = 1.0;

    for ( i = 1; i < round_num; i++ )
        mult = mult * 1.23;

    mult = mult + round_num * 0.12;
    return mult;
}

rogue_apply_round_scaling(round_num)
{
    if ( !isdefined( level.zombie_vars ) )
        return;

    mult = rogue_get_round_multiplier( round_num );
    base_health = maps\mp\zombies\_zm::ai_zombie_health( round_num );
    zombie_health = int( base_health * mult );

    if ( zombie_health < 180 )
        zombie_health = 180;

    level.zombie_health = zombie_health;
    spawn_delay = 0.70 - round_num * 0.045;

    if ( spawn_delay < 0.08 )
        spawn_delay = 0.08;

    level.zombie_vars["zombie_spawn_delay"] = spawn_delay;
    level.zombie_ai_limit = 24 + int( mult * 4.0 );

    if ( level.zombie_ai_limit > 70 )
        level.zombie_ai_limit = 70;

    level.zombie_actor_limit = level.zombie_ai_limit + 6;
    level.zombie_vars["zombie_ai_per_player"] = 6 + int( round_num * 0.8 + mult * 0.6 );
}

rogue_spawn_round_obstacles(round_num)
{
    wait 1.2;

    if ( !isdefined( level.rogue_started ) || !level.rogue_started )
        return;

    if ( !isdefined( level.zombie_spawners ) || level.zombie_spawners.size == 0 )
        return;

    extra_spawns = 1 + int( round_num / 2 );

    if ( round_num == 1 )
        extra_spawns = 3;
    else if ( round_num >= 8 )
        extra_spawns = extra_spawns + 2;

    for ( i = 0; i < extra_spawns; i++ )
    {
        spawner = level.zombie_spawners[randomint( level.zombie_spawners.size )];
        ai = maps\mp\zombies\_zm_utility::spawn_zombie( spawner, spawner.targetname, undefined, level.round_number );

        if ( isdefined( ai ) )
        {
            hp_boost = rogue_get_round_multiplier( round_num );

            if ( i == 0 && round_num == 1 )
                hp_boost = hp_boost * 2.8;
            else
                hp_boost = hp_boost * 1.2;

            ai.maxhealth = int( ai.maxhealth * hp_boost );
            ai.health = ai.maxhealth;
            ai.meleedamage = ai.meleedamage + int( round_num * 5 );
        }

        wait 0.10;
    }

    if ( isdefined( level.dog_spawners ) && level.dog_spawners.size > 0 && round_num >= 2 )
        maps\mp\zombies\_zm_ai_dogs::special_dog_spawn( undefined, 1 + int( round_num / 4 ) );
}
