// Minimal melee weapon stub for custom-map loader validation.

init( weapon_name, flourish_weapon_name, ballistic_weapon_name, ballistic_upgraded_weapon_name, cost, wallbuy_targetname, hint_string, vo_dialog_id, flourish_fn )
{
}

add_melee_weapon( weapon_name, flourish_weapon_name, ballistic_weapon_name, ballistic_upgraded_weapon_name, cost, wallbuy_targetname, hint_string, vo_dialog_id, flourish_fn )
{
}

prepare_stub( stub, weapon_name, flourish_weapon_name, ballistic_weapon_name, ballistic_upgraded_weapon_name, cost, wallbuy_targetname, hint_string, vo_dialog_id, flourish_fn )
{
    if ( isdefined( stub ) )
    {
        stub.weapon_name = weapon_name;
        stub.trigger_func = ::melee_weapon_think;
    }
}

add_stub( stub, weapon_name )
{
    if ( isdefined( stub ) )
    {
        stub.weapon_name = weapon_name;
        stub.trigger_func = ::melee_weapon_think;
    }
}

melee_weapon_think()
{
}

has_any_ballistic_knife()
{
    return 0;
}

has_upgraded_ballistic_knife()
{
    return 0;
}

change_melee_weapon( weapon, current_weapon )
{
    return current_weapon;
}

give_ballistic_knife( weapon_string, upgraded )
{
    return weapon_string;
}

give_melee_weapon_by_name( weapon_name )
{
    return weapon_name;
}

register_melee_weapon_for_level( weapon_name )
{
}
