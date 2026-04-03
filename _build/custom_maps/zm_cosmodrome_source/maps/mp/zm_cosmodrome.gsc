// Minimal stock-style zombies bootstrap for the custom cosmodrome lane.
#include common_scripts\utility;
#include maps\mp\gametypes_zm\_zm_gametype;
#include maps\mp\zm_cosmodrome_standard;

gamemode_callback_setup()
{
    println( "[cosmodrome] gamemode_callback_setup" );
    logprint( "[cosmodrome] gamemode_callback_setup\n" );
    add_map_gamemode( "zclassic", maps\mp\zm_cosmodrome::zclassic_preinit, undefined, undefined );
    add_map_location_gamemode( "zclassic", "cosmodrome", maps\mp\zm_cosmodrome_standard::precache, maps\mp\zm_cosmodrome_standard::main );
    add_map_gamemode( "zstandard", maps\mp\zm_cosmodrome::zstandard_preinit, undefined, undefined );
    add_map_location_gamemode( "zstandard", "cosmodrome", maps\mp\zm_cosmodrome_standard::precache, maps\mp\zm_cosmodrome_standard::main );
}

survival_init()
{
    println( "[cosmodrome] survival_init" );
    logprint( "[cosmodrome] survival_init\n" );
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
    println( "[cosmodrome] main_enter" );
    logprint( "[cosmodrome] main_enter\n" );
    level.default_game_mode = "zclassic";
    level.default_start_location = "cosmodrome";
    level.zombiemode = 1;
    level.riser_fx_on_client = 0;
    println( "[cosmodrome] main_ready" );
    logprint( "[cosmodrome] main_ready\n" );
}
