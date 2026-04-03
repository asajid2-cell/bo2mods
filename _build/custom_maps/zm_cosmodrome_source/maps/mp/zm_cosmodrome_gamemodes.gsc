#include common_scripts\utility;
#include maps\mp\_utility;
#include maps\mp\gametypes_zm\_zm_gametype;
#include maps\mp\zm_cosmodrome_standard;

init()
{
    add_map_gamemode( "zclassic", maps\mp\zm_cosmodrome::zclassic_preinit, undefined, undefined );
    add_map_location_gamemode( "zclassic", "cosmodrome", maps\mp\zm_cosmodrome_standard::precache, maps\mp\zm_cosmodrome_standard::main );
    add_map_gamemode( "zstandard", maps\mp\zm_cosmodrome::zstandard_preinit, undefined, undefined );
    add_map_location_gamemode( "zstandard", "cosmodrome", maps\mp\zm_cosmodrome_standard::precache, maps\mp\zm_cosmodrome_standard::main );
}
