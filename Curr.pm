#!/usr/bin/perl

package Curr;

sub new
{
    my $class = shift;
    my $self = {
        _name => shift,
        _value  => shift,
    };
    bless $self, $class;
    return $self;
}
sub TO_JSON { return { %{ shift() } }; }
1;
