// Minimal stock-carrier server script for running the cosmodrome world on the zm_transit slot.
#include common_scripts\utility;
#include maps\mp\gametypes_zm\_zm_gametype;
#include maps\mp\zm_cosmodrome_standard;

register_transit_carrier_clientfields()
{
    // Match the stock transit clientscript registration surface so the
    // carrier slot can survive startup without a clientfield mismatch.
    registerclientfield( "vehicle", "the_bus_spawned", 1, 1, "int" );
    registerclientfield( "vehicle", "bus_flashing_lights", 1, 1, "int" );
    registerclientfield( "vehicle", "bus_head_lights", 1, 1, "int" );
    registerclientfield( "vehicle", "bus_brake_lights", 1, 1, "int" );
    registerclientfield( "vehicle", "bus_turn_signal_left", 1, 1, "int" );
    registerclientfield( "vehicle", "bus_turn_signal_right", 1, 1, "int" );
    registerclientfield( "toplayer", "power_rumble", 1, 1, "int" );
    registerclientfield( "allplayers", "screecher_sq_lights", 1, 1, "int" );
    registerclientfield( "allplayers", "screecher_maxis_lights", 1, 1, "int" );
    registerclientfield( "allplayers", "sq_tower_sparks", 1, 1, "int" );
    registerclientfield( "allplayers", "navcard_held", 1, 4, "int" );
}

gamemode_callback_setup()
{
    println( "[cosmodrome_carrier] gamemode_callback_setup" );
    logprint( "[cosmodrome_carrier] gamemode_callback_setup\n" );
    add_map_gamemode( "zclassic", maps\mp\zm_transit::zclassic_preinit, undefined, undefined );
    add_map_location_gamemode( "zclassic", "town", maps\mp\zm_cosmodrome_standard::precache, maps\mp\zm_cosmodrome_standard::main );
    add_map_gamemode( "zstandard", maps\mp\zm_transit::zstandard_preinit, undefined, undefined );
    add_map_location_gamemode( "zstandard", "town", maps\mp\zm_cosmodrome_standard::precache, maps\mp\zm_cosmodrome_standard::main );
}

survival_init()
{
    println( "[cosmodrome_carrier] survival_init" );
    logprint( "[cosmodrome_carrier] survival_init\n" );
}

zclassic_preinit()
{
    survival_init();
}

zstandard_preinit()
{
    survival_init();
}

main()
{
    println( "[cosmodrome_carrier] main_enter" );
    logprint( "[cosmodrome_carrier] main_enter\n" );
    level.default_game_mode = "zclassic";
    level.default_start_location = "town";
    level.zombiemode = 1;
    level.riser_fx_on_client = 0;
    register_transit_carrier_clientfields();
    println( "[cosmodrome_carrier] main_ready" );
    logprint( "[cosmodrome_carrier] main_ready\n" );
}
