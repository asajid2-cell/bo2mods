#include common_scripts\utility;
#include maps\mp\_utility;

ensure_tables()
{
    if ( !isdefined( level.gamemode_map_location_init ) )
        level.gamemode_map_location_init = [];

    if ( !isdefined( level.gamemode_map_location_main ) )
        level.gamemode_map_location_main = [];

    if ( !isdefined( level.gamemode_map_location_precache ) )
        level.gamemode_map_location_precache = [];

    if ( !isdefined( level.gamemode_map_preinit ) )
        level.gamemode_map_preinit = [];

    if ( !isdefined( level.gamemode_map_postinit ) )
        level.gamemode_map_postinit = [];

    if ( !isdefined( level.gamemode_map_precache ) )
        level.gamemode_map_precache = [];

    if ( !isdefined( level.gamemode_map_main ) )
        level.gamemode_map_main = [];

    if ( !isdefined( level.cosmodrome_gamemode_vars ) )
        level.cosmodrome_gamemode_vars = [];
}

resolve_location()
{
    loc = getdvar( "ui_zm_mapstartlocation" );

    if ( loc == "" && isdefined( level.default_start_location ) )
        loc = level.default_start_location;

    return loc;
}

set_gamemode_var( name, value )
{
    ensure_tables();
    level.cosmodrome_gamemode_vars[name] = value;
}

set_gamemode_var_once( name, value )
{
    ensure_tables();

    if ( !isdefined( level.cosmodrome_gamemode_vars[name] ) )
        level.cosmodrome_gamemode_vars[name] = value;
}

get_gamemode_var( name )
{
    if ( !isdefined( level.cosmodrome_gamemode_vars ) )
        return undefined;

    if ( !isdefined( level.cosmodrome_gamemode_vars[name] ) )
        return undefined;

    return level.cosmodrome_gamemode_vars[name];
}

add_map_gamemode( mode, preinit_func, precache_func, main_func )
{
    ensure_tables();
    level.gamemode_map_preinit[mode] = preinit_func;
    level.gamemode_map_precache[mode] = precache_func;
    level.gamemode_map_main[mode] = main_func;
    level.gamemode_map_location_precache[mode] = [];
    level.gamemode_map_location_main[mode] = [];
}

add_map_location_gamemode( mode, location, precache_func, main_func )
{
    ensure_tables();

    if ( !isdefined( level.gamemode_map_location_precache[mode] ) )
        level.gamemode_map_location_precache[mode] = [];

    if ( !isdefined( level.gamemode_map_location_main[mode] ) )
        level.gamemode_map_location_main[mode] = [];

    level.gamemode_map_location_precache[mode][location] = precache_func;
    level.gamemode_map_location_main[mode][location] = main_func;
}

main()
{
    ensure_tables();
    println( "[cosmodrome] zm_gametype_main" );
    logprint( "[cosmodrome] zm_gametype_main\n" );
    level.zombiemode = 1;

    if ( !isdefined( level.default_game_mode ) )
        level.default_game_mode = "zclassic";

    if ( !isdefined( level.default_start_location ) )
        level.default_start_location = "cosmodrome";
}

post_gametype_main( gamemode )
{
    ensure_tables();
    loc = resolve_location();
    level.scr_zm_ui_gametype = gamemode;
    level.scr_zm_map_start_location = loc;
    set_gamemode_var_once( "mode", gamemode );
    set_gamemode_var_once( "location", loc );

    if ( isdefined( level.gamemode_map_preinit ) && isdefined( level.gamemode_map_preinit[gamemode] ) )
        [[ level.gamemode_map_preinit[gamemode] ]]();

    if ( isdefined( level.gamemode_map_postinit ) && isdefined( level.gamemode_map_postinit[gamemode] ) )
        [[ level.gamemode_map_postinit[gamemode] ]]();
}

rungametypeprecache( gamemode )
{
    ensure_tables();
    loc = resolve_location();

    if ( isdefined( level.gamemode_map_precache ) && isdefined( level.gamemode_map_precache[gamemode] ) )
        [[ level.gamemode_map_precache[gamemode] ]]();

    if ( isdefined( level.gamemode_map_location_precache ) && isdefined( level.gamemode_map_location_precache[gamemode] ) )
    {
        if ( isdefined( level.gamemode_map_location_precache[gamemode][loc] ) )
            [[ level.gamemode_map_location_precache[gamemode][loc] ]]();
    }
}

rungametypemain( gamemode, mode_main_func, use_round_logic )
{
    ensure_tables();
    loc = resolve_location();
    set_gamemode_var( "mode", gamemode );
    set_gamemode_var( "location", loc );

    if ( isdefined( level.gamemode_map_main ) && isdefined( level.gamemode_map_main[gamemode] ) )
        level thread [[ level.gamemode_map_main[gamemode] ]]();

    if ( isdefined( level.gamemode_map_location_main ) && isdefined( level.gamemode_map_location_main[gamemode] ) )
    {
        if ( isdefined( level.gamemode_map_location_main[gamemode][loc] ) )
            level thread [[ level.gamemode_map_location_main[gamemode][loc] ]]();
    }

    if ( isdefined( mode_main_func ) )
        level thread [[ mode_main_func ]]();
}

zclassic_main()
{
    println( "[cosmodrome] zclassic_main" );
    logprint( "[cosmodrome] zclassic_main\n" );

    if ( !flag_exists( "initial_blackscreen_passed" ) )
        flag_init( "initial_blackscreen_passed" );

    flag_set( "initial_blackscreen_passed" );
    level notify( "start_zombie_round_logic" );
}

setup_classic_gametype()
{
}

custom_spawn_init_func()
{
}

kill_all_zombies()
{
}

setup_standard_objects( location )
{
}

get_player_spawns_for_gametype()
{
    spawn_points = getentarray( "info_player_start_zm", "classname" );

    if ( isdefined( spawn_points ) && spawn_points.size > 0 )
        return spawn_points;

    spawn_points = getentarray( "info_player_start", "classname" );

    if ( isdefined( spawn_points ) && spawn_points.size > 0 )
        return spawn_points;

    return [];
}

post_init_gametype()
{
}

onspawnplayer()
{
}

track_encounters_win_stats( winning_team )
{
}

game_module_player_damage_callback( eattacker, einflictor, idamage, dflags, meansofdeath, weapon, vpoint, vdir, hitloc, psoffsettime )
{
}

end_rounds_early( winner )
{
}

init()
{
}
