stunned_callback( localclientnum, set )
{
    self.stunned = set;

    if ( set )
        self notify( "stunned" );
    else
        self notify( "not_stunned" );
}
