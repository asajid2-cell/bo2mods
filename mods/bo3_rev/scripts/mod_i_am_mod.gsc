init()
{
    bo3_rev_start();
}

main()
{
    bo3_rev_start();
}

bo3_rev_probe_weapon()
{
    return "mg08_zm";
}

bo3_rev_starter_weapon()
{
    return "mg08_zm";
}

bo3_rev_probe_mode()
{
    return "custom";
}

bo3_rev_probe_model_asset()
{
    return "bo3_rev_v2_idg_view_0312060433_e7b7b3";
}

bo3_rev_build_tag()
{
    return "0312060433_e7b7b3";
}

bo3_rev_demo_fast_spawn_delay()
{
    return 0.08;
}

bo3_rev_demo_default_hits_to_down()
{
    return 50;
}

bo3_rev_expected_clip()
{
    return 1;
}

bo3_rev_expected_engine_max()
{
    return 10;
}

bo3_rev_expected_hud_reserve()
{
    return 9;
}

bo3_rev_debug_enabled()
{
    return getdvarint( "bo3_rev_debug" ) == 1;
}

bo3_rev_start()
{
    if ( isdefined( level.bo3_rev_started ) )
        return;

    level.bo3_rev_started = 1;
    level.bo3_rev_servant_vortex_seq = 0;
    level.bo3_rev_demo_fast_spawns = 0;
    level.bo3_rev_demo_hits_to_down = bo3_rev_demo_default_hits_to_down();
    setdvar( "bo3_rev_debug", "0" );
    setdvar( "cg_drawScriptUsage", "0" );
    bo3_rev_init_effects();

    probe_weapon = bo3_rev_probe_weapon();
    starter_weapon = bo3_rev_starter_weapon();

    bo3_rev_log_event(
        "start",
        "stage=init"
        + ";build_tag=" + bo3_rev_build_tag()
        + ";map=" + getdvar( "mapname" )
        + ";zombiemode=" + bo3_rev_safe_str( level.zombiemode )
        + ";weapon=" + probe_weapon
        + ";starter=" + starter_weapon
        + ";mode=" + bo3_rev_probe_mode()
        + ";model=" + bo3_rev_probe_model_asset()
        + ";loadout=" + starter_weapon + "," + probe_weapon
        + ";expect_clip=" + bo3_rev_expected_clip()
        + ";expect_max=" + bo3_rev_expected_engine_max()
    );

    level thread bo3_rev_level_command_listener( "say" );
    level thread bo3_rev_level_command_listener( "sayall" );
    level thread bo3_rev_level_command_listener( "sayteam" );
    level thread bo3_rev_demo_spawn_tuner();
    level thread bo3_rev_on_player_connect();
}

bo3_rev_on_player_connect()
{
    for ( ;; )
    {
        level waittill( "connected", player );
        bo3_rev_log_event( "connect", "player_connected=1;build_tag=" + bo3_rev_build_tag() );
        if ( !isdefined( player.bo3_rev_command_listener_started ) )
        {
            player.bo3_rev_command_listener_started = 1;
            player thread bo3_rev_player_command_listener();
        }
        if ( !isdefined( player.bo3_rev_demo_health_watcher_started ) )
        {
            player.bo3_rev_demo_health_watcher_started = 1;
            player thread bo3_rev_demo_health_watcher();
        }
        player thread bo3_rev_on_player_spawn();
    }
}

bo3_rev_on_player_spawn()
{
    self endon( "disconnect" );

    for ( ;; )
    {
        self waittill( "spawned_player" );
        wait 0.30;

        if ( !bo3_rev_is_zombies_map() )
            continue;

        if ( bo3_rev_debug_enabled() && !isdefined( self.bo3_rev_state_watcher_started ) )
        {
            self.bo3_rev_state_watcher_started = 1;
            self thread bo3_rev_state_debug_watcher();
        }

        if ( !isdefined( self.bo3_rev_servant_fire_watcher_started ) )
        {
            self.bo3_rev_servant_fire_watcher_started = 1;
            self thread bo3_rev_servant_fire_watcher();
        }

        if ( bo3_rev_use_custom_viewmodel() && !isdefined( self.bo3_rev_viewmodel_watcher_started ) )
        {
            self.bo3_rev_viewmodel_watcher_started = 1;
            self thread bo3_rev_viewmodel_swap_watcher();
        }

        bo3_rev_grant_starting_loadout();
        self bo3_rev_apply_demo_health( 0 );
    }
}

bo3_rev_is_zombies_map()
{
    if ( isdefined( level.zombiemode ) && level.zombiemode )
        return true;

    map_name = tolower( getdvar( "mapname" ) );
    if ( isdefined( map_name ) && map_name.size >= 3 )
    {
        prefix = getsubstr( map_name, 0, 3 );
        if ( prefix == "zm_" || prefix == "so_" )
            return true;
    }

    return false;
}

bo3_rev_grant_starting_loadout()
{
    probe_weapon = bo3_rev_probe_weapon();
    starter_weapon = bo3_rev_starter_weapon();

    bo3_rev_log_player_state( self, "pre_grant" );

    if ( bo3_rev_use_custom_viewmodel() )
        bo3_rev_prepare_low_bone_viewmodel();

    if ( !self hasweapon( starter_weapon ) )
    {
        self giveweapon( starter_weapon );
        wait 0.05;
    }

    bo3_rev_log_weapon_probe( self, "pre_shell_give", probe_weapon );

    gave_ok = bo3_rev_try_give_weapon( probe_weapon );

    bo3_rev_log_weapon_probe( self, "post_shell_give", probe_weapon );

    if ( self hasweapon( probe_weapon ) && probe_weapon != "m1911_zm" && self hasweapon( "m1911_zm" ) )
    {
        self takeweapon( "m1911_zm" );
        wait 0.05;
    }

    if ( self hasweapon( "m14_zm" ) && probe_weapon != "m14_zm" )
    {
        self takeweapon( "m14_zm" );
        wait 0.05;
    }

    self switchtoweaponimmediate( probe_weapon );
    wait 0.05;
    if ( self getcurrentweapon() != probe_weapon )
    {
        self switchtoweapon( probe_weapon );
        wait 0.05;
    }

    bo3_rev_log_player_state( self, "post_switch" );
    bo3_rev_log_event(
        "grant",
        "weapon=" + probe_weapon
        + ";starter=" + starter_weapon
        + ";build_tag=" + bo3_rev_build_tag()
        + ";gave_ok=" + gave_ok
        + ";switch_ok=" + ( self getcurrentweapon() == probe_weapon )
        + ";current=" + bo3_rev_safe_str( self getcurrentweapon() )
        + ";expect_clip=" + bo3_rev_expected_clip()
        + ";expect_max=" + bo3_rev_expected_engine_max()
    );
    self iprintln( "^2bo3_rev:^7 probe active [" + bo3_rev_build_tag() + "]: " + probe_weapon + " HUD should read " + bo3_rev_expected_clip() + "/" + bo3_rev_expected_hud_reserve() + " if override won" );
}

bo3_rev_use_custom_viewmodel()
{
    return false;
}

bo3_rev_level_command_listener(event_name)
{
    for ( ;; )
    {
        level waittill( event_name, arg1, arg2, arg3, arg4 );

        player = bo3_rev_find_player_arg( arg1, arg2, arg3, arg4 );
        bo3_rev_try_handle_chat_arg( player, arg1, event_name );
        bo3_rev_try_handle_chat_arg( player, arg2, event_name );
        bo3_rev_try_handle_chat_arg( player, arg3, event_name );
        bo3_rev_try_handle_chat_arg( player, arg4, event_name );
    }
}

bo3_rev_player_command_listener()
{
    self endon( "disconnect" );
    self thread bo3_rev_player_say_listener( "say" );
    self thread bo3_rev_player_say_listener( "sayall" );
    self thread bo3_rev_player_say_listener( "sayteam" );
}

bo3_rev_player_say_listener(event_name)
{
    self endon( "disconnect" );

    for ( ;; )
    {
        self waittill( event_name, arg1, arg2, arg3, arg4 );
        bo3_rev_try_handle_chat_arg( self, arg1, event_name + "_self" );
        bo3_rev_try_handle_chat_arg( self, arg2, event_name + "_self" );
        bo3_rev_try_handle_chat_arg( self, arg3, event_name + "_self" );
        bo3_rev_try_handle_chat_arg( self, arg4, event_name + "_self" );
    }
}

bo3_rev_find_player_arg(arg1, arg2, arg3, arg4)
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

bo3_rev_try_handle_chat_arg(player, arg, event_name)
{
    if ( !isdefined( arg ) || isplayer( arg ) )
        return;

    text = bo3_rev_normalize_chat_text( "" + arg );

    if ( text == "" )
        return;

    if ( isdefined( player ) && isplayer( player ) && getdvarint( "bo3_rev_chat_debug" ) == 1 )
        player iprintln( "^3chat seen [" + event_name + "]:^7 " + text );

    bo3_rev_try_handle_chat_command( player, text );
}

bo3_rev_normalize_chat_text(text)
{
    if ( !isdefined( text ) || text == "" )
        return "";

    t = tolower( text );

    while ( t != "" && getsubstr( t, 0, 1 ) == " " )
        t = getsubstr( t, 1, t.size );

    if ( t == "" )
        return "";

    // Some builds prepend a broken first character before the actual chat payload.
    if ( t[0] != "." && t[0] != "/" && t[0] != "p" && t[0] != "r" && t[0] != "f" && t[0] != "h" && t[0] != "d" )
        t = getsubstr( t, 1, t.size );

    return t;
}

bo3_rev_try_handle_chat_command(source_player, raw_text)
{
    if ( !isdefined( raw_text ) || raw_text == "" || isplayer( raw_text ) )
        return;

    text = tolower( "" + raw_text );
    parts = strtok( text, " " );

    if ( !isdefined( parts ) || parts.size < 1 )
        return;

    token = parts[0];
    if ( !isdefined( token ) || token == "" )
        return;

    if ( token == ".p" || token == "/p" || token == "p" )
    {
        if ( isdefined( source_player ) && isplayer( source_player ) )
            source_player bo3_rev_handle_pay_command( parts );
        return;
    }

    if ( token == ".round" || token == "/round" || token == "round" )
    {
        if ( isdefined( source_player ) && isplayer( source_player ) )
            source_player bo3_rev_handle_round_command( parts );
        return;
    }

    if ( token == ".fast" || token == "/fast" || token == "fast" )
    {
        if ( isdefined( source_player ) && isplayer( source_player ) )
            source_player bo3_rev_handle_fast_command( parts );
        return;
    }

    if ( token == ".hits" || token == "/hits" || token == "hits" )
    {
        if ( isdefined( source_player ) && isplayer( source_player ) )
            source_player bo3_rev_handle_hits_command( parts );
        return;
    }

    if ( token == ".debug" || token == "/debug" || token == "debug" )
    {
        if ( isdefined( source_player ) && isplayer( source_player ) )
            source_player bo3_rev_handle_debug_command( parts );
        return;
    }
}

bo3_rev_handle_pay_command(parts)
{
    if ( !isdefined( parts ) || parts.size < 2 )
    {
        self iprintlnbold( "^3Usage:^7 .p 10000" );
        return;
    }

    amount = int( parts[1] );
    if ( amount <= 0 )
    {
        self iprintlnbold( "^1Invalid amount." );
        return;
    }

    if ( amount > 100000 )
        amount = 100000;

    self maps\mp\zombies\_zm_score::add_to_player_score( amount );

    bo3_rev_log_event(
        "chat_cmd",
        "cmd=.p"
        + ";player=" + bo3_rev_safe_str( self.name )
        + ";amount=" + amount
        + ";new_score=" + bo3_rev_safe_str( self.score )
    );

    self iprintlnbold( "^2Paid:^7 " + amount + " ^3(total:^7 " + self.score + "^3)" );
}

bo3_rev_handle_round_command(parts)
{
    if ( !isdefined( parts ) || parts.size < 2 )
    {
        self iprintlnbold( "^3Usage:^7 .round 15" );
        return;
    }

    target_round = int( parts[1] );
    current_round = 1;

    if ( isdefined( level.round_number ) )
        current_round = level.round_number;

    if ( target_round <= current_round )
    {
        self iprintlnbold( "^1Round must be greater than current round (" + current_round + ")." );
        return;
    }

    if ( isdefined( level.bo3_rev_round_jump_active ) && level.bo3_rev_round_jump_active )
    {
        self iprintlnbold( "^1Round change already in progress." );
        return;
    }

    if ( target_round > 255 )
        target_round = 255;

    bo3_rev_log_event(
        "chat_cmd",
        "cmd=.round"
        + ";player=" + bo3_rev_safe_str( self.name )
        + ";from=" + current_round
        + ";to=" + target_round
    );

    self iprintlnbold( "^2Round jump starting:^7 " + current_round + " ^2->^7 " + target_round );
    level thread bo3_rev_force_round_forward( target_round, self );
}

bo3_rev_handle_fast_command(parts)
{
    new_state = !level.bo3_rev_demo_fast_spawns;

    if ( isdefined( parts ) && parts.size >= 2 )
    {
        arg = parts[1];

        if ( arg == "on" || arg == "1" || arg == "true" )
            new_state = 1;
        else if ( arg == "off" || arg == "0" || arg == "false" )
            new_state = 0;
    }

    level.bo3_rev_demo_fast_spawns = new_state;

    bo3_rev_log_event(
        "chat_cmd",
        "cmd=.fast"
        + ";player=" + bo3_rev_safe_str( self.name )
        + ";enabled=" + new_state
        + ";spawn_delay=" + bo3_rev_demo_fast_spawn_delay()
    );

    if ( new_state )
        bo3_rev_broadcast_command_message( "^2Fast spawns:^7 ON ^3(delay:^7 " + bo3_rev_demo_fast_spawn_delay() + "^3)" );
    else
        bo3_rev_broadcast_command_message( "^1Fast spawns:^7 OFF" );
}

bo3_rev_handle_hits_command(parts)
{
    if ( !isdefined( parts ) || parts.size < 2 )
    {
        self iprintlnbold( "^3Usage:^7 .hits 50 ^3(current:^7 " + level.bo3_rev_demo_hits_to_down + "^3)" );
        return;
    }

    hits = int( parts[1] );

    if ( hits < 1 )
        hits = 1;

    if ( hits > 200 )
        hits = 200;

    level.bo3_rev_demo_hits_to_down = hits;
    bo3_rev_apply_demo_health_to_all_players( 0 );

    bo3_rev_log_event(
        "chat_cmd",
        "cmd=.hits"
        + ";player=" + bo3_rev_safe_str( self.name )
        + ";hits=" + hits
        + ";max_health=" + bo3_rev_demo_target_max_health()
    );

    bo3_rev_broadcast_command_message(
        "^2Demo hits-to-down:^7 " + hits
        + " ^3(max health:^7 " + bo3_rev_demo_target_max_health() + "^3)"
    );
}

bo3_rev_handle_debug_command(parts)
{
    new_state = !bo3_rev_debug_enabled();

    if ( isdefined( parts ) && parts.size >= 2 )
    {
        arg = parts[1];

        if ( arg == "on" || arg == "1" || arg == "true" )
            new_state = 1;
        else if ( arg == "off" || arg == "0" || arg == "false" )
            new_state = 0;
    }

    setdvar( "bo3_rev_debug", new_state );
    setdvar( "cg_drawScriptUsage", new_state );

    if ( new_state )
        bo3_rev_enable_debug_watchers_for_all_players();

    bo3_rev_log_event(
        "chat_cmd",
        "cmd=.debug"
        + ";player=" + bo3_rev_safe_str( self.name )
        + ";enabled=" + new_state
    );

    if ( new_state )
        bo3_rev_broadcast_command_message( "^2Debug overlay:^7 ON" );
    else
        bo3_rev_broadcast_command_message( "^1Debug overlay:^7 OFF" );
}

bo3_rev_force_round_forward(target_round, source_player)
{
    if ( isdefined( level.bo3_rev_round_jump_active ) && level.bo3_rev_round_jump_active )
        return;

    level.bo3_rev_round_jump_active = 1;

    if ( target_round < 1 )
        target_round = 1;

    common_scripts\utility::flag_clear( "spawn_zombies" );
    bo3_rev_kill_all_active_enemies();

    level.time_bomb_round_change = 1;
    level.zombie_round_start_delay = 0;
    level.zombie_round_end_delay = 0;
    between_round_time = level.zombie_vars["zombie_between_round_time"];
    level.zombie_vars["zombie_between_round_time"] = 0;
    level notify( "end_of_round" );
    common_scripts\utility::flag_set( "end_round_wait" );
    maps\mp\zombies\_zm::ai_calculate_health( target_round );

    if ( isdefined( level._time_bomb ) && isdefined( level._time_bomb.round_initialized ) && level._time_bomb.round_initialized )
    {
        level._time_bomb.restoring_initialized_round = 1;
        target_round--;
    }

    level.round_number = target_round;
    setroundsplayed( target_round );

    bo3_rev_log_event(
        "round_cmd",
        "stage=commit"
        + ";target=" + target_round
        + ";player=" + bo3_rev_safe_str( source_player )
    );

    if ( isdefined( source_player ) && isplayer( source_player ) )
        source_player iprintlnbold( "^2Forcing round:^7 " + target_round );

    level waittill( "between_round_over" );

    level.zombie_round_start_delay = undefined;
    level.time_bomb_round_change = undefined;
    level.zombie_vars["zombie_between_round_time"] = between_round_time;
    common_scripts\utility::flag_clear( "end_round_wait" );
    common_scripts\utility::flag_set( "spawn_zombies" );
    level.bo3_rev_round_jump_active = 0;

    bo3_rev_log_event(
        "round_cmd",
        "stage=done"
        + ";round=" + bo3_rev_safe_str( level.round_number )
    );

    bo3_rev_broadcast_command_message( "^2Round advanced:^7 " + level.round_number );
}

bo3_rev_kill_all_active_enemies()
{
    team = "axis";
    if ( isdefined( level.zombie_team ) )
        team = level.zombie_team;

    zombies = getaispeciesarray( team, "all" );
    if ( !isdefined( zombies ) || !isarray( zombies ) )
        return;

    for ( i = 0; i < zombies.size; i++ )
    {
        if ( !isdefined( zombies[i] ) || !isalive( zombies[i] ) )
            continue;

        zombies[i] dodamage( zombies[i].health + 10000, zombies[i].origin );

        if ( i % 3 == 0 )
            wait 0.05;
    }
}

bo3_rev_demo_capture_spawn_defaults()
{
    if ( isdefined( level.bo3_rev_demo_spawn_defaults_captured ) && level.bo3_rev_demo_spawn_defaults_captured )
        return true;

    if ( !isdefined( level.zombie_vars ) )
        return false;

    if ( !isdefined( level.zombie_vars["zombie_spawn_delay"] ) || !isdefined( level.zombie_vars["zombie_between_round_time"] ) )
        return false;

    level.bo3_rev_demo_default_spawn_delay = level.zombie_vars["zombie_spawn_delay"];
    level.bo3_rev_demo_default_between_round_time = level.zombie_vars["zombie_between_round_time"];
    level.bo3_rev_demo_default_round_start_delay = level.zombie_round_start_delay;
    level.bo3_rev_demo_default_round_end_delay = level.zombie_round_end_delay;
    level.bo3_rev_demo_spawn_defaults_captured = 1;
    return true;
}

bo3_rev_demo_restore_spawn_defaults()
{
    if ( !isdefined( level.bo3_rev_demo_spawn_defaults_captured ) || !level.bo3_rev_demo_spawn_defaults_captured )
        return;

    if ( !isdefined( level.zombie_vars ) )
        return;

    level.zombie_vars["zombie_spawn_delay"] = level.bo3_rev_demo_default_spawn_delay;
    level.zombie_vars["zombie_between_round_time"] = level.bo3_rev_demo_default_between_round_time;

    if ( isdefined( level.bo3_rev_demo_default_round_start_delay ) )
        level.zombie_round_start_delay = level.bo3_rev_demo_default_round_start_delay;
    else
        level.zombie_round_start_delay = undefined;

    if ( isdefined( level.bo3_rev_demo_default_round_end_delay ) )
        level.zombie_round_end_delay = level.bo3_rev_demo_default_round_end_delay;
    else
        level.zombie_round_end_delay = undefined;
}

bo3_rev_demo_spawn_tuner()
{
    level endon( "game_ended" );
    level.bo3_rev_demo_fast_spawns_last = -1;

    for ( ;; )
    {
        wait 0.25;

        if ( !bo3_rev_is_zombies_map() )
            continue;

        if ( !bo3_rev_demo_capture_spawn_defaults() )
            continue;

        if ( level.bo3_rev_demo_fast_spawns )
        {
            if ( isdefined( level.zombie_vars ) )
            {
                level.zombie_vars["zombie_spawn_delay"] = bo3_rev_demo_fast_spawn_delay();
                level.zombie_vars["zombie_between_round_time"] = 0;
            }

            level.zombie_round_start_delay = 0;
            level.zombie_round_end_delay = 0;
            level.bo3_rev_demo_fast_spawns_last = 1;
            continue;
        }

        if ( level.bo3_rev_demo_fast_spawns_last == 1 )
        {
            if ( isdefined( level.bo3_rev_round_jump_active ) && level.bo3_rev_round_jump_active )
                continue;

            bo3_rev_demo_restore_spawn_defaults();
            level.bo3_rev_demo_fast_spawns_last = 0;
        }
    }
}

bo3_rev_demo_target_max_health()
{
    hits = bo3_rev_demo_default_hits_to_down();

    if ( isdefined( level.bo3_rev_demo_hits_to_down ) )
        hits = level.bo3_rev_demo_hits_to_down;

    if ( hits < 1 )
        hits = 1;

    return hits * 50;
}

bo3_rev_apply_demo_health(preserve_ratio)
{
    if ( !isplayer( self ) || !isalive( self ) )
        return;

    if ( isdefined( self.laststand ) && self.laststand )
        return;

    target_max = bo3_rev_demo_target_max_health();
    old_max = self.maxhealth;

    if ( !isdefined( old_max ) || old_max <= 0 )
        old_max = self.health;

    if ( !isdefined( old_max ) || old_max <= 0 )
        old_max = 100;

    old_ratio = 1.0;
    if ( isdefined( self.health ) && self.health > 0 )
        old_ratio = self.health / old_max;

    if ( old_ratio > 1.0 )
        old_ratio = 1.0;

    self setmaxhealth( target_max );

    if ( preserve_ratio )
    {
        min_ratio = 2.0 / target_max;
        if ( old_ratio < min_ratio )
            old_ratio = min_ratio;

        self setnormalhealth( old_ratio );
    }
    else
        self.health = self.maxhealth;
}

bo3_rev_apply_demo_health_to_all_players(preserve_ratio)
{
    players = getplayers();
    if ( !isdefined( players ) || !isarray( players ) )
        return;

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isplayer( players[i] ) )
            continue;

        players[i] bo3_rev_apply_demo_health( preserve_ratio );
    }
}

bo3_rev_enable_debug_watchers_for_all_players()
{
    players = getplayers();
    if ( !isdefined( players ) || !isarray( players ) )
        return;

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isplayer( players[i] ) )
            continue;

        if ( !isdefined( players[i].bo3_rev_state_watcher_started ) )
        {
            players[i].bo3_rev_state_watcher_started = 1;
            players[i] thread bo3_rev_state_debug_watcher();
        }
    }
}

bo3_rev_demo_health_watcher()
{
    self endon( "disconnect" );

    for ( ;; )
    {
        wait 0.50;

        if ( !bo3_rev_is_zombies_map() )
            continue;

        if ( !isalive( self ) )
            continue;

        if ( isdefined( self.laststand ) && self.laststand )
            continue;

        target_max = bo3_rev_demo_target_max_health();

        if ( !isdefined( self.maxhealth ) || self.maxhealth != target_max )
            self bo3_rev_apply_demo_health( 1 );
    }
}

bo3_rev_broadcast_command_message(text)
{
    players = getplayers();
    if ( !isdefined( players ) || !isarray( players ) )
        return;

    for ( i = 0; i < players.size; i++ )
    {
        if ( !isdefined( players[i] ) || !isplayer( players[i] ) )
            continue;

        players[i] iprintlnbold( text );
    }
}

bo3_rev_init_effects()
{
    if ( !isdefined( level._effect ) )
        level._effect = [];

    level._effect["bo3_rev_servant_vortex_loop"] = loadfx( "maps/zombie_tomb/fx_tomb_screecher_vortex" );
    level._effect["bo3_rev_servant_vortex_glow"] = loadfx( "maps/zombie_tomb/fx_tomb_vortex_glow" );
    level._effect["bo3_rev_servant_vortex_burst"] = loadfx( "maps/zombie_tomb/fx_tomb_ee_vortex" );
    level._effect["bo3_rev_servant_vortex_end"] = loadfx( "maps/zombie/fx_zmb_blackhole_trap_end" );
    level._effect["bo3_rev_servant_vortex_lightning"] = loadfx( "maps/zombie/fx_zombie_dog_lightning_spawn" );
    level._effect["bo3_rev_servant_fire_smoke"] = loadfx( "weapon/thunder_gun/fx_thundergun_smoke_cloud" );
}

bo3_rev_prepare_low_bone_viewmodel()
{
    cur_vm = self getviewmodel();
    target_vm = bo3_rev_bridge_viewmodel();

    if ( !isdefined( self.bo3_rev_default_vm ) || self.bo3_rev_default_vm == "" )
    {
        if ( isdefined( cur_vm ) && cur_vm != "" && cur_vm != target_vm )
            self.bo3_rev_default_vm = cur_vm;
    }

    if ( cur_vm == target_vm )
    {
        bo3_rev_log_event(
            "viewmodel",
            "stage=pre_grant_already_low"
            + ";vm=" + bo3_rev_safe_str( cur_vm )
            + ";target=" + target_vm
        );
        return;
    }

    precachemodel( target_vm );
    self setviewmodel( target_vm );
    wait 0.05;

    bo3_rev_log_event(
        "viewmodel",
        "stage=pre_grant_low"
        + ";from=" + bo3_rev_safe_str( cur_vm )
        + ";to=" + bo3_rev_safe_str( self getviewmodel() )
        + ";target=" + target_vm
        + ";default=" + bo3_rev_safe_str( self.bo3_rev_default_vm )
    );
}

bo3_rev_try_give_weapon(weapon)
{
    if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
        return false;

    if ( self hasweapon( weapon ) )
        return true;

    self giveweapon( weapon );
    wait 0.05;
    bo3_rev_log_event(
        "give_path",
        "weapon=" + weapon
        + ";path=giveweapon"
        + ";has=" + self hasweapon( weapon )
        + ";cur=" + bo3_rev_safe_str( self getcurrentweapon() )
    );

    if ( self hasweapon( weapon ) )
    {
        self bo3_rev_give_max_ammo( weapon );
        return true;
    }

    self giveweapon( weapon, 0 );
    wait 0.05;
    bo3_rev_log_event(
        "give_path",
        "weapon=" + weapon
        + ";path=giveweapon0"
        + ";has=" + self hasweapon( weapon )
        + ";cur=" + bo3_rev_safe_str( self getcurrentweapon() )
    );

    if ( self hasweapon( weapon ) )
    {
        self bo3_rev_give_max_ammo( weapon );
        return true;
    }

    if ( isdefined( maps\mp\zombies\_zm_weapons::weapon_give ) )
    {
        self maps\mp\zombies\_zm_weapons::weapon_give( weapon, 0, 1, 1 );
        wait 0.05;
        bo3_rev_log_event(
            "give_path",
            "weapon=" + weapon
            + ";path=weapon_give_safe"
            + ";has=" + self hasweapon( weapon )
            + ";cur=" + bo3_rev_safe_str( self getcurrentweapon() )
        );

        if ( self hasweapon( weapon ) )
        {
            self bo3_rev_give_max_ammo( weapon );
            return true;
        }

        self maps\mp\zombies\_zm_weapons::weapon_give( weapon, 0, 0 );
        wait 0.05;
        bo3_rev_log_event(
            "give_path",
            "weapon=" + weapon
            + ";path=weapon_give_force"
            + ";has=" + self hasweapon( weapon )
            + ";cur=" + bo3_rev_safe_str( self getcurrentweapon() )
        );

        if ( self hasweapon( weapon ) )
        {
            self bo3_rev_give_max_ammo( weapon );
            return true;
        }
    }

    return false;
}

bo3_rev_give_max_ammo(weapon)
{
    if ( !isdefined( weapon ) || weapon == "" || weapon == "none" )
        return;

    clip = weaponclipsize( weapon );
    max_ammo = weaponmaxammo( weapon );

    if ( isdefined( clip ) )
        self setweaponammoclip( weapon, clip );

    if ( isdefined( max_ammo ) )
        self setweaponammostock( weapon, max_ammo );
}

bo3_rev_state_debug_watcher()
{
    self endon( "disconnect" );

    last_wpn = "";
    last_vm = "";

    for ( ;; )
    {
        wait 0.25;

        if ( !bo3_rev_is_zombies_map() )
            continue;

        if ( !bo3_rev_debug_enabled() )
        {
            last_wpn = "";
            last_vm = "";
            continue;
        }

        cur_wpn = self getcurrentweapon();
        cur_vm = self getviewmodel();

        if ( !isdefined( cur_wpn ) )
            cur_wpn = "<undef>";
        if ( !isdefined( cur_vm ) )
            cur_vm = "<undef>";

        if ( cur_wpn != last_wpn || cur_vm != last_vm )
        {
            bo3_rev_log_player_state( self, "state_change" );
            last_wpn = cur_wpn;
            last_vm = cur_vm;
        }
    }
}

bo3_rev_target_viewmodel()
{
    return "bo3_rev_idg_viewhands";
}

bo3_rev_bridge_viewmodel()
{
    return "bo3_rev_bridge_viewhands";
}

bo3_rev_viewmodel_swap_watcher()
{
    self endon( "disconnect" );

    if ( !isdefined( self.bo3_rev_default_vm ) || self.bo3_rev_default_vm == "" )
        self.bo3_rev_default_vm = self getviewmodel();

    for ( ;; )
    {
        wait 0.05;

        if ( !bo3_rev_is_zombies_map() )
            continue;

        cur_wpn = self getcurrentweapon();
        cur_vm = self getviewmodel();
        target_vm = bo3_rev_target_viewmodel();
        bridge_vm = bo3_rev_bridge_viewmodel();
        probe_weapon = bo3_rev_probe_weapon();

        if ( !isdefined( self.bo3_rev_default_vm ) || self.bo3_rev_default_vm == "" || self.bo3_rev_default_vm == "viewmodel_usa_no_model" || self.bo3_rev_default_vm == target_vm || self.bo3_rev_default_vm == bridge_vm )
        {
            if ( isdefined( cur_vm ) && cur_vm != "" && cur_vm != "viewmodel_usa_no_model" && cur_vm != target_vm && cur_vm != bridge_vm )
                self.bo3_rev_default_vm = cur_vm;
        }

        if ( cur_wpn == probe_weapon )
        {
            if ( cur_vm != target_vm )
            {
                precachemodel( target_vm );
                self setviewmodel( target_vm );
                wait 0.01;
                bo3_rev_log_event(
                    "viewmodel",
                    "stage=set"
                    + ";from=" + bo3_rev_safe_str( cur_vm )
                    + ";to=" + bo3_rev_safe_str( self getviewmodel() )
                    + ";target=" + target_vm
                    + ";cur=" + bo3_rev_safe_str( cur_wpn )
                );
            }
        }
        else
        {
            if ( isdefined( self.bo3_rev_default_vm ) && self.bo3_rev_default_vm != "" && cur_vm != self.bo3_rev_default_vm )
            {
                self setviewmodel( self.bo3_rev_default_vm );
                wait 0.01;
                bo3_rev_log_event(
                    "viewmodel",
                    "stage=restore"
                    + ";from=" + bo3_rev_safe_str( cur_vm )
                    + ";to=" + bo3_rev_safe_str( self getviewmodel() )
                    + ";cur=" + bo3_rev_safe_str( cur_wpn )
                );
            }
        }
    }
}

bo3_rev_servant_cooldown_ms()
{
    return 850;
}

bo3_rev_servant_duration()
{
    // BO3 black_hole_bomb_zm uses fuseTime 4.0, and the vortex duration is
    // driven directly from that fuse in _zm_weap_black_hole_bomb.gsc.
    return 4.0;
}

bo3_rev_servant_pull_radius()
{
    return 384;
}

bo3_rev_servant_kill_radius()
{
    return 88;
}

bo3_rev_servant_trace_distance()
{
    return 2200;
}

bo3_rev_servant_drag_step()
{
    return 72;
}

bo3_rev_servant_drag_travel_time()
{
    return 0.10;
}

bo3_rev_servant_lightning_interval()
{
    return 1.10;
}

bo3_rev_servant_lightning_height()
{
    return 18;
}

bo3_rev_servant_fire_watcher()
{
    self endon( "disconnect" );

    for ( ;; )
    {
        self waittill( "weapon_fired" );

        if ( !bo3_rev_is_zombies_map() )
            continue;

        if ( self getcurrentweapon() != bo3_rev_probe_weapon() )
            continue;

        now = gettime();
        if ( isdefined( self.bo3_rev_servant_last_fire_ms ) && now - self.bo3_rev_servant_last_fire_ms < bo3_rev_servant_cooldown_ms() )
            continue;

        if ( isdefined( self.bo3_rev_servant_active_vortex ) && isdefined( self.bo3_rev_servant_active_vortex.bo3_rev_active ) && self.bo3_rev_servant_active_vortex.bo3_rev_active )
        {
            bo3_rev_log_event(
                "servant_fire",
                "stage=blocked_active"
                + ";build_tag=" + bo3_rev_build_tag()
                + ";weapon=" + bo3_rev_probe_weapon()
                + ";vortex_id=" + bo3_rev_safe_str( self.bo3_rev_servant_active_vortex.bo3_rev_id )
            );
            continue;
        }

        self.bo3_rev_servant_last_fire_ms = now;
        self thread bo3_rev_servant_fire_once();
    }
}

bo3_rev_servant_fire_once()
{
    origin = bo3_rev_servant_trace_origin();
    flash = self gettagorigin( "tag_flash" );
    if ( isdefined( flash ) )
        playfx( level._effect["bo3_rev_servant_fire_smoke"], flash - self getplayerviewheight() );

    bo3_rev_log_event(
        "servant_fire",
        "stage=trigger"
        + ";build_tag=" + bo3_rev_build_tag()
        + ";weapon=" + bo3_rev_probe_weapon()
        + ";origin=" + bo3_rev_safe_str( origin )
    );

    self thread bo3_rev_servant_spawn_vortex( origin );
}

bo3_rev_servant_trace_origin()
{
    start = self getweaponmuzzlepoint();
    forward = self getweaponforwarddir();
    end = start + vectorscale( forward, bo3_rev_servant_trace_distance() );
    trace = bullettrace( start, end, 0, self );

    if ( isdefined( trace ) && isdefined( trace["position"] ) )
        origin = trace["position"];
    else
        origin = end;

    floor_trace = bullettrace( origin + ( 0, 0, 48 ), origin + ( 0, 0, -256 ), 0, undefined );
    if ( isdefined( floor_trace ) && isdefined( floor_trace["position"] ) )
        origin = floor_trace["position"] + ( 0, 0, 16 );

    return origin;
}

bo3_rev_servant_spawn_vortex(origin)
{
    vortex = spawn( "script_origin", origin );
    if ( !isdefined( vortex ) )
        return;

    level.bo3_rev_servant_vortex_seq++;
    vortex.bo3_rev_active = 1;
    vortex.bo3_rev_id = level.bo3_rev_servant_vortex_seq;
    vortex.bo3_rev_owner = self;
    vortex.bo3_rev_weapon = bo3_rev_probe_weapon();
    vortex.bo3_rev_pulls = 0;
    vortex.bo3_rev_kills = 0;
    self.bo3_rev_servant_active_vortex = vortex;

    bo3_rev_log_event(
        "servant_vortex",
        "stage=spawn"
        + ";build_tag=" + bo3_rev_build_tag()
        + ";id=" + vortex.bo3_rev_id
        + ";origin=" + bo3_rev_safe_str( vortex.origin )
        + ";duration=" + bo3_rev_servant_duration()
    );

    playfx( level._effect["bo3_rev_servant_vortex_burst"], vortex.origin );
    vortex.bo3_rev_fx_loop = bo3_rev_spawn_loop_fx( "bo3_rev_servant_vortex_loop", vortex.origin );
    vortex.bo3_rev_fx_glow = bo3_rev_spawn_loop_fx( "bo3_rev_servant_vortex_glow", vortex.origin );

    vortex thread bo3_rev_servant_vortex_lightning_loop();
    vortex thread bo3_rev_servant_vortex_loop();
}

bo3_rev_servant_vortex_lightning_loop()
{
    self endon( "death" );
    self endon( "bo3_rev_servant_stop" );

    while ( isdefined( self ) && isdefined( self.bo3_rev_active ) && self.bo3_rev_active )
    {
        playfx(
            level._effect["bo3_rev_servant_vortex_lightning"],
            self.origin + ( 0, 0, bo3_rev_servant_lightning_height() )
        );
        wait bo3_rev_servant_lightning_interval();
    }
}

bo3_rev_servant_vortex_loop()
{
    self endon( "death" );

    end_time = gettime() + int( bo3_rev_servant_duration() * 1000 );

    while ( gettime() < end_time && isdefined( self ) && self.bo3_rev_active )
    {
        bo3_rev_servant_affect_zombies( self );
        wait 0.10;
    }

    if ( isdefined( self ) )
    {
        self.bo3_rev_active = 0;
        self notify( "bo3_rev_servant_stop" );

        if ( isdefined( self.bo3_rev_owner ) && isplayer( self.bo3_rev_owner ) && isdefined( self.bo3_rev_owner.bo3_rev_servant_active_vortex ) && self.bo3_rev_owner.bo3_rev_servant_active_vortex == self )
            self.bo3_rev_owner.bo3_rev_servant_active_vortex = undefined;

        bo3_rev_log_event(
            "servant_vortex",
            "stage=end"
            + ";build_tag=" + bo3_rev_build_tag()
            + ";id=" + self.bo3_rev_id
            + ";pulls=" + self.bo3_rev_pulls
            + ";kills=" + self.bo3_rev_kills
        );

        playfx( level._effect["bo3_rev_servant_vortex_end"], self.origin );
        bo3_rev_cleanup_loop_fx( self.bo3_rev_fx_loop );
        bo3_rev_cleanup_loop_fx( self.bo3_rev_fx_glow );
        self delete();
    }
}

bo3_rev_spawn_loop_fx(key, origin)
{
    if ( !isdefined( level._effect[key] ) )
        return undefined;

    fx_ent = spawnfx( level._effect[key], origin );
    if ( isdefined( fx_ent ) )
        triggerfx( fx_ent );
    return fx_ent;
}

bo3_rev_cleanup_loop_fx(fx_ent)
{
    if ( isdefined( fx_ent ) )
        fx_ent delete();
}

bo3_rev_servant_affect_zombies(vortex)
{
    if ( !isdefined( vortex ) || !isdefined( vortex.bo3_rev_active ) || !vortex.bo3_rev_active )
        return;

    team = "axis";
    if ( isdefined( level.zombie_team ) )
        team = level.zombie_team;

    zombies = getaispeciesarray( team, "all" );
    if ( !isdefined( zombies ) || !isarray( zombies ) )
        return;

    pull_radius_sq = bo3_rev_servant_pull_radius() * bo3_rev_servant_pull_radius();
    kill_radius_sq = bo3_rev_servant_kill_radius() * bo3_rev_servant_kill_radius();

    for ( i = 0; i < zombies.size; i++ )
    {
        zombie = zombies[i];

        if ( !isdefined( zombie ) || !isalive( zombie ) )
            continue;

        dist_sq = distancesquared( zombie.origin, vortex.origin );

        if ( dist_sq > pull_radius_sq )
            continue;

        if ( dist_sq <= kill_radius_sq )
        {
            zombie bo3_rev_servant_kill_zombie( vortex.bo3_rev_owner, vortex, "inner" );
            continue;
        }

        zombie bo3_rev_servant_pull_zombie_step( vortex, vortex.bo3_rev_owner, dist_sq );
    }
}

bo3_rev_servant_pull_zombie_step(vortex, owner, dist_sq)
{
    if ( !isdefined( self ) || !isalive( self ) )
        return;

    if ( !isdefined( vortex ) || !isdefined( vortex.bo3_rev_active ) || !vortex.bo3_rev_active )
        return;

    if ( !isdefined( self.bo3_rev_servant_pull_mark ) || self.bo3_rev_servant_pull_mark != vortex.bo3_rev_id )
    {
        self.bo3_rev_servant_pull_mark = vortex.bo3_rev_id;
        vortex.bo3_rev_pulls++;
    }

    target = bo3_rev_servant_step_toward( self.origin, vortex.origin, bo3_rev_servant_drag_step() );
    self setgoalpos( target );

    // Avoid per-zombie helper entities; only force the inner band inward.
    if ( dist_sq <= ( bo3_rev_servant_pull_radius() * bo3_rev_servant_pull_radius() * 0.25 ) )
        self forceteleport( target, self.angles );
}

bo3_rev_servant_step_toward(from, to, step)
{
    dir = vectornormalize( to - from );
    if ( !isdefined( dir ) )
        return from;

    next = from + vectorscale( dir, step );
    floor_trace = bullettrace( next + ( 0, 0, 48 ), next + ( 0, 0, -256 ), 0, undefined );
    if ( isdefined( floor_trace ) && isdefined( floor_trace["position"] ) )
        next = floor_trace["position"];

    return next;
}

bo3_rev_servant_kill_zombie(owner, vortex, reason)
{
    if ( !isdefined( self ) || !isalive( self ) )
        return;

    if ( isdefined( self.bo3_rev_servant_killed ) && self.bo3_rev_servant_killed )
        return;

    self.bo3_rev_servant_killed = 1;

    if ( isdefined( vortex ) )
        vortex.bo3_rev_kills++;

    playfx( level._effect["bo3_rev_servant_vortex_end"], self.origin + ( 0, 0, 24 ) );
    self dodamage( self.health + 1000, self.origin, owner, owner, "none", "MOD_SUICIDE", 0, bo3_rev_probe_weapon() );
}

bo3_rev_log_weapon_probe(player, stage, weapon)
{
    clip = weaponclipsize( weapon );
    max_ammo = weaponmaxammo( weapon );

    bo3_rev_log_event(
        "weapon_probe",
        "stage=" + stage
        + ";build_tag=" + bo3_rev_build_tag()
        + ";weapon=" + weapon
        + ";has=" + player hasweapon( weapon )
        + ";can_use=" + player player_can_use_content( weapon )
        + ";clip=" + bo3_rev_safe_str( clip )
        + ";max=" + bo3_rev_safe_str( max_ammo )
        + ";expect_clip=" + bo3_rev_expected_clip()
        + ";expect_max=" + bo3_rev_expected_engine_max()
        + ";override_won=" + ( isdefined( clip ) && isdefined( max_ammo ) && clip == bo3_rev_expected_clip() && max_ammo == bo3_rev_expected_engine_max() )
    );
}

bo3_rev_log_player_state(player, stage)
{
    if ( !isdefined( player ) || !isplayer( player ) )
    {
        bo3_rev_log_event( "player_state", "stage=" + stage + ";player=<invalid>" );
        return;
    }

    starter_weapon = bo3_rev_starter_weapon();
    probe_weapon = bo3_rev_probe_weapon();
    cur = player getcurrentweapon();
    vm = player getviewmodel();
    inv = player getweaponslist( 1 );
    inv_count = 0;
    if ( isdefined( inv ) && isarray( inv ) )
        inv_count = inv.size;

    bo3_rev_log_event(
        "player_state",
        "stage=" + stage
        + ";build_tag=" + bo3_rev_build_tag()
        + ";probe=" + probe_weapon
        + ";cur=" + bo3_rev_safe_str( cur )
        + ";vm=" + bo3_rev_safe_str( vm )
        + ";has_starter=" + player hasweapon( starter_weapon )
        + ";has_probe=" + player hasweapon( probe_weapon )
        + ";inv_count=" + inv_count
        + ";inv=" + bo3_rev_join_weapons_compact( inv, 10 )
    );
}

bo3_rev_join_weapons_compact(weapons, cap)
{
    if ( !isdefined( weapons ) || !isarray( weapons ) )
        return "[]";

    if ( !isdefined( cap ) || cap < 1 )
        cap = 8;

    out = "";
    for ( i = 0; i < weapons.size && i < cap; i++ )
    {
        if ( i > 0 )
            out += ",";
        out += bo3_rev_safe_str( weapons[i] );
    }

    if ( weapons.size > cap )
        out += ",+more(" + ( weapons.size - cap ) + ")";

    return "[" + out + "]";
}

bo3_rev_log_event(event_name, msg)
{
    line = "[bo3_rev][" + bo3_rev_safe_str( event_name ) + "][t=" + gettime() + "] " + bo3_rev_safe_str( msg );
    println( line );
    logprint( line + "\n" );
}

bo3_rev_safe_str(v)
{
    if ( !isdefined( v ) )
        return "<undef>";
    return "" + v;
}
