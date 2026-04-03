#include common_scripts\utility;

precache()
{
}

main()
{
    println( "[cosmodrome] standard_main_wait" );
    logprint( "[cosmodrome] standard_main_wait\n" );
    flag_wait( "initial_blackscreen_passed" );
    println( "[cosmodrome] standard_main_power_on" );
    logprint( "[cosmodrome] standard_main_power_on\n" );
    flag_set( "power_on" );
}
