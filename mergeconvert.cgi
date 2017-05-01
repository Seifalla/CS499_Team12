#!/usr/bin/perl -w 

=head1 SYNOPSYS
Web-based interface to my convert.pl program, but entirely inline.
Author: Raphael Finkel 1/2015 © GPL
=cut
use Data::Dumper;
use LWP::UserAgent qw( );
use LWP::ConnCache;
use Locale::Currency;
use Curr;
use JSON::PP;
use Scalar::Util qw(looks_like_number);
use Time::Piece;
use strict;
use utf8;
use CGI qw/:standard -debug/;
$ENV{'PATH'} = '/bin:/usr/bin:/usr/local/bin:/usr/local/gnu/bin'; # for security

# constants
my $dim= 0;
my $query=new CGI;
my $submit = $query->param('submit');
my $reset = $query->param('reset');
my $text;
my $Dim = $query->param('Dim');
my $Unit = $query->param('Unit');
my $drop = $query->param('drop');
my @array;
my $selection = "";
my $unitbutton = "";
# HTML for first drop down 
my $DimDrop= "
        <form
        action='" . $0 . "'
        method='post'>
                  <select name='drop'>
			<option>$drop</option>
                        <option value='Length'>Length</option>
			<option value='Mass'>Mass</option>
                        <option value='Area'>Area</option>
                        <option value='Volume'>Volume</option>
                        <option value='Velocity'>Velocity</option>
                        <option value='Energy'>Energy</option>
                        <option value='Time'>Time</option>
			<option value='Force'>Force</option>
			<option value='Dollars'>Dollars</option>
			<option value='Misc'>Misc</option>
                  </select>";
#HTML for second drop down and text area
my $DimButton = "
      <input  type='submit' value='enter' name='Dim'/>";

my $opentext = "</br>
                Enter your conversion requests here:<br/><textarea
                name='text' cols='80' rows='10' onmouseover='this.focus()'>";

my $closetext ="</textarea>
                <br/>
                <input type='submit' name='submit' value='submit'
                        style='background-color:#AAFFAA;'/>
                <input type='submit' name='reset' value='reset'
                        style='background-color:#FFAAAA;'/>
        </form>
        ";
my $css = '
	pre,textarea {
		font-family: "Courier", monospace;
		font-size: 100%; 
		font-weight: bold;
	}
	h1 {
		font-size: 300%;
		text-align: center;
	}
';
# mass, distance, time, current, luminosity, count, temperature
# dimension symbols: mass, length, time, current, luminosity, 
	# number, temperature
my @names = ('x', 'kg', 'm', 's', 'A', 'cd', 'mol', "°K", 'USD');
my $zero = [0.0, 0,0,0,0,0,0,0,0];
my $bad = ['NaN', "",0,0,0,0,0,0,0]; # The first dim holds an error string
my %constants = (
	g => [1.0,   1,0,0,0,0,0,0,0],
	m => [1.0,   0,1,0,0,0,0,0,0],
	s => [1.0,   0,0,1,0,0,0,0,0],
	A => [1.0,   0,0,0,1,0,0,0,0],
	cd => [1.0,  0,0,0,0,1,0,0,0], # candela
	mol => [1.0,   0,0,0,0,0,1,0,0],
	K => [1.0,   0,0,0,0,0,0,1,0],
    USD => [1.0,   0,0,0,0,0,0,0,1],
); # constants
my %cNames = {
	s => 'second',
	m => 'meter',
	g => 'gram',
	A => 'Ampere',
	cd => 'candela',
	mol => 'mole',
	K => 'degree Kelvin',
    USD => 'dollar',
};
my %multipliers = (
	P => 1e+15, # peta-
	T => 1e+12, # tera-
	G => 1e+9, # giga-
	M => 1e+6, # mega-
	k => 1000.0,  # kilo-
	h => 100.0,   # hecto-
	d => 0.1, 	# deci-
	c => 0.01,  # centi-
	m => 0.001, # milli-
	μ => 1e-06, # micro-
	n => 1e-09, # nano-
	p => 1e-12, # pico-
	f => 1e-15, # femto-
);
#arrays for dropw down categories
my @area = ();
my @mass = ();
my @length = ();
my @volume = ();
my @velocity = ();
my @energy = ();
my @time = ();
my @force = ();
my @dollar = ();
my @misc = ();

sub init {
	my ($title);
	binmode STDOUT, ":utf8";
	binmode STDERR, ":utf8";
	binmode STDIN, ":utf8";
	$title = 'Units' unless defined($title) and $title ne '';
	my $analytics = `cat analytics.txt`;
	# my $analytics = ''; # disabled for now
	print header(-type=>"text/html", -charset=>'UTF-8') .
		start_html(-encoding=>"UTF-8",
			-title=>$title,
			-style=>{code => '.clickable:hover {background-color:lime;}'},
			-script=>$analytics,
			-style=>{-code=>$css},
		) .
		h1("Unit converter and calculator");
} # init

#Additions to function by Ronnel Turner: 
#Main of the page
sub doWork {
	my $hidden = "hidden";
        my $text = $query->param('text');
	#Decision making for if user presses submit, reset, or enter
	if ($submit eq "submit") {
                print "You entered: <pre>$text</pre>";
                print "Result:<pre>";
                readEvalPrint($text);
                print :"</pre>";
	}
	 else { 
 		#clears values for reset
                if($reset eq "reset")
		{
			$text = "";

		}
		# if user selected drop down
		elsif($Dim){
			# gets units for that length and populates drop down
			$selection = "<select name ='units'>";
			my @array = getUnits($drop);
		      	foreach my $index(@array)
			{	
				#stores key as drop down value
				$selection = $selection. "<option value=$index>$index</br>";
			}
			$selection = $selection."</select>";
			$unitbutton = "<input type='submit' value='enter' name='Unit'/>";
                }
		#if user sleects a specific units
          	elsif($Unit){
			#add unit to text area
			$text = $query->param('text').$query->param('units');
		}
		print $DimDrop.$DimButton.$selection.$unitbutton.$opentext.$text.$closetext. br() . hr() . br().
		"<pre>
Type in expressions or assignments followed by newline.
Accepted Commands:
1. 'convert x to y', where x and y are any compatible expressions.
2. 'dimof x', where x is a unit
3. 'addim x name y', where y is a new dimension and x is unit in it
4. Assignment using '='
5. To comment start a line with '%'

You may use metric prefixes, such as M, μ, and n. 
You may use exponentiation (with ^) to any integer (including negative).
You may say 'convert x to y', where x and y are any compatible expressions.
You may not use e notation

You may prefix constants and variables with multipliers: 
	P peta-
	T tera-
	G giga-
	M mega-
	k kilo-
	h hecto-
	d deci-
	c centi-
	m milli-
	μ micro-
	n nano-
	p pico-
	f femto-
</pre>";
	showConstants();
	}
} # doWork

sub finalize {
	# $form =~ s/entry/entry1/g;
	print end_html(), "\n";
} # finalize

# global variables
	my %variables = (
	);

# arithmetic

sub toPower {
	my ($dimVal, $power) = @_;
	if (int($power) != $power) {
		return (valError("non-integer power"));
	}
	my $base = ${$dimVal}[0];
	my $value = 1;
	my $count = $power;
	while ($count) {
		if ($count > 0) {
			$value *= $base;
			$count -= 1;
		} else {
			$value /= $base;
			$count += 1;
		}
	} # while count
	my $answer = [$value];
	for my $index (1 .. $#{$dimVal}) {
		push @$answer, ${$dimVal}[$index] * $power;
	}
	return $answer;
} # toPower

sub copyVal { # shallow copy
	my ($val) = @_;
	my $answer = [];
	for my $component (@$val) {
		push @$answer, $component;
	}
	return $answer;
} # copyVal

sub valError {
	my ($msg) = @_;
	my $answer = copyVal($bad);
	${$answer}[1] = $msg;
	return($answer);
} # valError

sub parseError {
	my ($query, $msg) = @_;
	my $answer = copyVal($bad);
	${$answer}[1] = $msg;
	# print "Parse error: $msg; remaining query is $query\n";
	return($query, $answer);
} # parseError

sub doOp {
	my ($first, $second, $operator) = @_;
	my $answer;
	my ($val1, $val2) = (${$first}[0], ${$second}[0]);
	if ($val1 eq 'NaN' and $val2 eq 'NaN') { # two errors; compound them
		return(valError("${$first}[1], ${$second}[1]"));
	}
	return $first if ($val1 eq 'NaN');
	return $second if ($val2 eq 'NaN');
	if ($operator =~ /[+\-]/) { # addition/subtraction
		if (!isSameDim($first, $second)) {
			return (valError "dimension error");
		}
		$answer = $operator eq '+'
			? [$val1 + $val2] : [$val1 - $val2];
		for my $index (1 .. $#{$first}) {
			push @$answer, ${$first}[$index];
		}
	} elsif ($operator =~ /[\*\/]/) { # multiplication/division
		if ($operator eq '/' and $val2 eq 0) {
			return (valError "division by 0");
		}
		$answer = $operator eq '*'
			? [$val1 * $val2] : [$val1 / $val2];
		for my $index (1 .. $#{$first}) {
			push @$answer, $operator eq '*'
				? ${$first}[$index] + ${$second}[$index]
				: ${$first}[$index] - ${$second}[$index];
		}
	} else {
		return (valError "Unknown operator $operator");
	}
	return $answer;
} # doOp

# lexical analyzer
sub match {
	my ($query, $token) = @_;
	if ($query =~ s/^\s*\Q$token\E//s) {
		return($query);
	} else {
		warn("expected $token but did not find it\n");
		return($query);
	}
} # match

# all parsing routines take a query, return (remainder, expansion)

sub isSameDim {
        my ($a, $b) = @_;
        for my $index (1 .. $#{$a}) {
		#To populate constants hash table
		return 0 if (${$a}[$index] != ${$b}[$index]);
                
       
        }
        return 1;
} # isSameDim

sub isScalar {
	my ($dimVal) = @_;
	for my $index (1 .. $#{$dimVal}) {
		return 0 if (${$dimVal}[$index]);
	}
	return 1;
} # isSameDim

sub valToString {
	my ($dimVal) = @_;
	my @pos = ();
	my @neg = ();
	my $exponent;
	my $val = ${$dimVal}[0];
	# adjust g to kg for printing purposes
	my $gramExponent = $val eq 'NaN' ? 0 : ${$dimVal}[1];
	# print "gramExponent is $gramExponent\n";
	while ($gramExponent) {
		if ($gramExponent > 0) {
			$val /= 1000.0;
			$gramExponent -= 1;
		} else {
			$val *= 1000;
			$gramExponent += 1;
		}
	} # while count
	return ("invalid: ${$dimVal}[1]") if $val eq 'NaN';
	for my $index (1 .. $#{$dimVal}) {
		$exponent = ${$dimVal}[$index];
		if ($exponent > 0) {
			push @pos, $names[$index] .
				($exponent == 1 ? '' : "^$exponent");
		} elsif ($exponent < 0) {
			$exponent = -$exponent;
			push @neg, $names[$index] .
				($exponent == 1 ? '' : "^$exponent");
		}
	}
	$val .= ' ' if @pos;
	if (@neg > 1) {
		return "$val" . join(' ', @pos) . '/(' . join(' ', @neg) .
			')';
	} elsif (@neg == 1) {
		return "$val" . join(' ', @pos) . '/' . join(' ', @neg);
	} elsif (!@neg) {
		return "$val" . join(' ', @pos);
	} else {
		return "I can't handle this value: " . Dumper($dimVal);
	}
} # valToString 

sub printVal {
	my ($msg, $val) = @_;
	print $msg . valToString($val);
} # printVal

# recursive-descent parser. 

sub expr { # the main routine
	my ($query) = @_;
	my (@first, @rest);
	# print "expr: $query\n";
	my $first;
	($query, $first) = terms($query);
	# printVal "first: ", $first;
	if ($query =~ s/^\s*([+\-])//) { # an operator
		my $operator = $1;
		my $second;
		($query, $second) = expr($query);
		return ($query, doOp($first, $second, $operator));
	} else { # no operator
		return ($query, $first);
	} # no operator
} # expr

sub terms {
	my ($query) = @_;
	my (@first, @rest);
	# print "terms: $query\n";
	my $first;
	($query, $first) = primary($query);
	if ($query =~ s/^\s*([*\/\w\(])//) { 
		my $operator = $1;
		if ($operator =~ /[\w\(]/) { # implicit multiplication
			$query = "$operator$query"; # replace stolen character
			$operator = '*';
			# print "implicit multiplication\n";
		}
		my $second;
		($query, $second) = terms($query);
		# printVal "Second is ", $second;
		return ($query, doOp($first, $second, $operator));
	} else {
		return ($query, $first);
	}
} # terms

sub primary {
	my ($query) = @_;
	# print "primary: $query\n";
	my ($contents, $answer);
	my $token;
	if ($query =~ s/^\s*-//) { # negation
		($query, $contents) = primary($query);
		$answer = copyVal($contents);
		${$answer}[0] = -${$answer}[0];
		return($query, $answer);
	}
	if ($query =~ s/^\s*\(//) {
		($query, $contents) = expr($query);
		$query = match($query, ')');
		# printVal "parenthesized expression; returning ", $contents;
		$answer = $contents;
	} elsif ($query =~ s/^\s*([\d\.]+)//) { # number
		$token = $1;
		if ($token =~ /\..*\./) { # multiple decimal points
			print "$token is invalid; assuming zero.\n";
			return ($query, $zero);
		}
		$answer = [$token, 0,0,0,0,0,0,0];
		# printVal "returning number: ", $answer;
	} elsif ($query =~ s/^\s*(\w+)//) { # id
		$token = $1;
		# try looking up the id
		$answer = $variables{$token};
		if (!defined($answer)) { # not a variable; try a constant
			$answer = $constants{$token};
		}
		if (!defined($answer)) { # not a constant, try multiplier
			if ($token =~ /^(.)(\w+)$/ && defined($multipliers{$1})
					&& defined($constants{$2})) {
				my ($multiplier, $unit) = ($1, $2);
				$answer = copyVal($constants{$unit});
				${$answer}[0] *= $multipliers{$multiplier};
			} # will work
		} # try a multiplier prefix
	}
	if (defined($answer)) {
		# printVal "got id: ", $answer;
		if ($query =~ s/^\s*\^//) { # exponent
			my ($rest, $exponent) = primary($query);
			if (isScalar($exponent)) {
				return ($rest, toPower($answer, ${$exponent}[0]));
			} else {
				return parseError($rest, "exponent is not scalar");
			}
		} else { # no exponent
			return ($query, $answer);
		}
	} elsif (defined($token)) {
		return parseError($query, "\"$token\" is not defined");
	} else {
		return parseError($query, "missing token");
	}
} # primary

# a wrapper around expr()
sub parseExpr {
	my ($string) = @_;
	return ('') if ($string =~ /^\s*$/); # trivial case
	my ($extra, $results) = expr($string);
	# printVal "parseExpr: result will be ", $results;
	if ($extra =~ /\S/) {
		return valError("$string is malformed before '$extra'");
	}
	return $results;
} # parseExpr

# Author: Seifalla Moustafa; this function checks if the JSON file has expired

sub isFileValid {

    my $base_path = "./currencies.json";

    my $fh = 'currencies.json';

# stat returns an array containing status information about the file
# the ninth element is the date in which the file was last modified

    my $epoch_timestamp = (stat($fh))[9];
    my $timestamp = localtime($epoch_timestamp);

    my $currentTime = localtime();

    my $format = '%a %b %d %H:%M:%S %Y';

# calculate how long the file has lived since it was last modified

    my $diff = Time::Piece->strptime($currentTime, $format) - Time::Piece->strptime($timestamp, $format);

# if the file exists and it's younger than six hours, return true

    if (-f $base_path && $diff < 21600){
    
    	return 1;}
   else{			# return false
	return 0;}
}

# Seifalla Moustafa; this function adds entries to the hash table containing the currencies values

sub addCurrencies {

# if the file is empty or outdated, load the currencies from the api, else populate the hash table with the file's data.

    if (isFileValid()) {

	loadJson();
    }
    else {
 	loadApi();   
  }
}

# Seifalla Moustafa; this function makes api calls to load the new currencies values

sub loadApi {

# instantiate a browser object to send a GET request

my $browser = LWP::UserAgent->new();

# use a built-in function to load all the currencies' names into an array

    my @codes   = all_currency_codes();

    my @currencies = ();

# USD is the base unit. All the currencies will be converted to usd.

  $codes[0] = 'USD';

  my $a = 0;

  my $lastKnownCurrency = 'USD';

  my $url = '';

# Since we're dealing with one server, we're going to use a persistent connection.

  my $conn_cache = LWP::ConnCache->new;
  $conn_cache->total_capacity([1]) ;
  $browser->conn_cache($conn_cache) ;

# for each currency: 
#	- make an api call to calculate its equivalent value in dollars
#	- store it in hash table
#	- add it to the currencies array
# Note: this api supports 70 currencies

  while($a < 70){
    $url = 'https://www.exchangerate-api.com/'.$codes[$a+1].'/'.$codes[$a].'/1.00?k=9f915924bc0ff6c59b9cb71d';
    my $response = $browser->get($url);
    if($response->content > 0){
    $lastKnownCurrency = $codes[$a+1];
    my $result = $response->content .' '.$codes[$a];
    $constants{$codes[$a+1]} = parseExpr $result;
    $cNames{$codes[$a+1]} = code2currency($codes[$a+1]);
    my $currency = new Curr($codes[$a+1], ${$constants{$codes[$a+1]}}[0]);
    push(@currencies, $currency);
    $a = $a + 1;
    }
    else{
	$codes[$a+1] = $lastKnownCurrency;
	$a = $a + 1;
    }
  }
 
 # convert the currencies' array into JSON format and store it in the JSON file
 
  my $JSON = JSON::PP->new->utf8;
  $JSON->convert_blessed(1);
  my $json = $JSON->encode(\@currencies);
  open my $fh, ">", "currencies.json";
  print $fh $json;
  close $fh;
}

# Seifalla Moustafa; this function loads the currencies from the JSON file and stores them into the hash
# table.

sub loadJson {

# open a file in "read" mode

	 local $/; #Enable 'slurp' mode
  	 open my $fh, "<", "currencies.json";
  	 my $json = <$fh>;
  	 close $fh;
# decode the file content and store it in an array
	 my $data = decode_json($json);
	 
# for each object in the array, store the value member in the hash table
	for my $currency (@{$data}){

		my $Cname = '';
		my $value = 0;

		for my $key (keys(%$currency)){
		
			my $name = $currency->{$key};

# determine if the data member is the currency name or its value

                	if (looks_like_number($name)){
				$value = $name;
                	}
                	else{
				$Cname = $name;
                	}
		}
		$constants{$Cname} = parseExpr $value .' USD';
		$cNames{$Cname} = code2currency($Cname);
	}
}

# Seifalla Moustafa; this function displays the dimensions of the input unit

sub dimof {

# this array contains the 8 base dimensions

	my @dims = ('mass', 'length', 'time', 'current', 'luminosity', 'mole', "temperature", 'currency');

# store the value of the argument in a variable

        my ($a) = @_;

# initialize the array counter to 0

        my $dimCount = 0;
        my $dim = "";
	my $denominator;
	my $numerator;

# the dimensions of a unit are stored in an array.
# the following two loops translate the array to an arithmatic expression
# for example, if the array is [1,1,0,0,0,0,0,0], it will
# be translated to mass/length
# the first loop builds the numerator, and the second one builds the denominator.

        for my $index (1 .. $#{$a}){

                if(${$a}[$index] != 0){
                        if(${$a}[$index] == 1) {
				if(defined($numerator)){
                                	$numerator = "$numerator*".$dims[$dimCount];
				}
				else{$numerator = "$numerator".$dims[$dimCount];}
                        } elsif(${$a}[$index] > 1) {
				if(defined($numerator)){
                                	$numerator = "$numerator*".$dims[$dimCount] . "^" . ${$a}[$index];
				}
				else{$numerator = "$numerator".$dims[$dimCount] . "^" . ${$a}[$index];}
                        }
			else {}
                }
                $dimCount = $dimCount + 1;
        }

	$dimCount = 0;

	for my $index (1 .. $#{$a}){

		if(${$a}[$index] != 0){

			if(${$a}[$index] == -1) {
				if(defined($denominator)){
					$denominator = "$denominator*".$dims[$dimCount];
				} else {$denominator = "$denominator".$dims[$dimCount];}
			}
			elsif(${$a}[$index] < -1) {
                                my $sign = -1 * ${$a}[$index];
				if(defined($denominator)){
                                	$denominator = "$denominator*".$dims[$dimCount] . "^" . $sign;
				} else {$denominator = "$denominator".$dims[$dimCount] . "^" . $sign;}
                        }
			else {}
		}
		$dimCount = $dimCount + 1;
	}

	# the denominator should be surrounded by parenthesis

	if(defined($denominator)){

		$denominator = "("."$denominator".")";
	}
	if(!defined($numerator)){

		$numerator = "1";
	}

	if(defined($denominator)){

		$dim = "($numerator)"."/"."$denominator";
	}
	else{
		$dim = $numerator;
	}

	# if the function failed to translate the input,
	# it will return an error.

	if(!defined($denominator) && $numerator == "1"){

		$dim = "invalid input";
	}

        return $dim;
}

sub addSIUnits { # Système international d'unités
	$constants{'cc'} = parseExpr('cm^3');
		$cNames{'cc'} = 'cubic centimeter';
	$constants{'l'} = parseExpr('1000 cc'); # liter
		$cNames{'l'} = 'liter';
	$constants{'hectare'} = parseExpr('(100 m)^2'); # hectare
		$cNames{'hectare'} = 'hectare';
	$constants{'dunam'} = parseExpr('1000 m^2'); # dunam (Ottoman)
		$cNames{'dunam'} = 'dunam';
	$constants{'Hz'} = parseExpr('1/s'); # Hertz (frequency)
		$cNames{'Hz'} = 'Hertz';
	$constants{'Å'} = parseExpr('m / 10^10'); # Angstrom 
		$cNames{'Å'} = 'Angstrom';
	$constants{'N'} = parseExpr('kg * m / s^2'); # Newton
		$cNames{'N'} = 'Newton';
	$constants{'J'} = parseExpr('N * m'); # joule
		$cNames{'J'} = 'Joule';
	$constants{'W'} = parseExpr('J / s'); # watt
		$cNames{'W'} = 'Watt';
	$constants{'Pa'} = parseExpr('N / m^2'); # pascal
		$cNames{'Pa'} = 'Pascal';
	$constants{'C'} = parseExpr('s * A'); # coulomb
		$cNames{'C'} = 'Coulomb';
	$constants{'V'} = parseExpr('W / A'); # volt
		$cNames{'V'} = 'Volt';
	$constants{'F'} = parseExpr('C / V'); # farad (capacitance)
		$cNames{'F'} = 'Farad';
	$constants{'Ω'} = parseExpr('V / A'); # ohm (resistance)
		$cNames{'Ω'} = 'Ohm';
	$constants{'S'} = parseExpr('A / V'); # siemens (conductance)
		$cNames{'S'} = 'Siemens';
	$constants{'Wb'} = parseExpr('V * s'); # weber (magnetic flux)
		$cNames{'Wb'} = 'Weber';
	$constants{'Ts'} = parseExpr('Wb / m^2'); # tesla (flux density)
		$cNames{'Ts'} = 'Tesla';
	$constants{'H'} = parseExpr('Wb / A'); # henry (inductance)
		$cNames{'H'} = 'Henry';
	$constants{'Gy'} = parseExpr('J / kg'); # gray (absorbed dose)
		$cNames{'Gy'} = 'Gray';
	$constants{'Sv'} = parseExpr('J / kg'); # sievert (equiv dose)
		$cNames{'Sv'} = 'Sievert';
	$constants{'kat'} = parseExpr('mol / s'); # katal (catalytic act)
		$cNames{'kat'} = 'katal';
	$constants{'Rvalue'} = parseExpr('m^2 K / W'); # insulation
		$cNames{'Rvalue'} = 'R value';
	$constants{'molal'} = parseExpr('mol / kg');
		$cNames{'molal'} = 'molal';
} # addSIUnits

sub addPhysicsConstants { # measured quantities
	$constants{'c'} = parseExpr('299792458m/s'); # speed of light
		$cNames{'c'} = 'speed of light';
	$constants{'L'} = parseExpr('6.02214 10^23 / mol');
		$cNames{'L'} = 'Avogadro\'s number';
		# Avogadro's number
	$constants{'F'} = parseExpr('96485.3365 C/mol'); 
		$cNames{'F'} = 'Faraday constant';
		# Faraday constant
	$constants{'e'} = parseExpr('F / L'); # charge on an electron
		$cNames{'e'} = 'electron charge';
	$constants{'k_e'} = parseExpr('8.987551 10^9 N m^2 / C^2'); 
		$cNames{'k_e'} = 'Coulomb constant';
		# Coulomb constant
	$constants{'G'} = parseExpr('(6.67384/10^11) m^3 / (kg s^2) '); 
		$cNames{'G'} = 'gravitational constant';
		# Gravitational constant
	$constants{'R'} = parseExpr('8.314 (J/K mol)'); # gas constant
		$cNames{'R'} = 'gas constant';
	$constants{'h'} = parseExpr('6.62606957 10^-34 J s'); # Planck constant
		$cNames{'h'} = 'Planck constant';
	$constants{'π'} = parseExpr('3.1415926535');
		$cNames{'π'} = 'pi';
	$constants{'ℏ'} = parseExpr('h/(2 * π)'); # Dirac constant
		$cNames{'ℏ'} = 'Dirac constant';
} # addPhysicsConstants

sub addEnglishUnits {
	# http://en.wikipedia.org/wiki/United_States_customary_units
	# distance
	$constants{'ft'} = parseExpr('0.3048 m'); # international foot
		$cNames{'ft'} = 'foot';
	$constants{'yd'} = parseExpr('3 ft'); # yard
		$cNames{'yd'} = 'yard';
	$constants{'ftm'} = parseExpr('2 yd'); # fathom
		$cNames{'ftm'} = 'fathom';
	$constants{'cb'} = parseExpr('120 ftm'); # cable
		$cNames{'cb'} = 'cable';
	$constants{'rd'} = parseExpr('16.5 ft'); # rod
		$cNames{'rd'} = 'rod';
	$constants{'ch'} = parseExpr('4 rd'); # chain
		$cNames{'ch'} = 'chain';
	$constants{'fur'} = parseExpr('10 ch'); # furlong
		$cNames{'fur'} = 'furlong';
	$constants{'in'} = parseExpr('ft/12');
		$cNames{'in'} = 'inch';
	$constants{'mi'} = parseExpr('5280 ft'); # mile
		$cNames{'mi'} = 'mile';
	$constants{'nmi'} = parseExpr('1.151 mi'); # nautical mile
		$cNames{'nmi'} = 'nautical mile';
	$constants{'lea'} = parseExpr('3 mi'); # league
		$cNames{'lea'} = 'league';
	# area
	$constants{'acre'} = parseExpr('mi^2 / 640 ');
		$cNames{'acre'} = 'acre';
	$constants{'twp'} = parseExpr('4 lea^2'); # survey township
		$cNames{'twp'} = 'township';
	# volume (liquid)
	$constants{'minim'} = parseExpr('61.611519922 μl'); # minim
		$cNames{'minim'} = 'minim';
	$constants{'fldr'} = parseExpr('60 minim'); # fluid dram
		$cNames{'fldr'} = 'fluid dram';
	$constants{'tsp'} = parseExpr('80 minim'); # teaspoon
		$cNames{'tsp'} = 'teaspoon';
	$constants{'tbsp'} = parseExpr('3 tsp'); # teaspoon
		$cNames{'tbsp'} = 'tablespoon';
	$constants{'floz'} = parseExpr('2 tbsp'); # fluid ounce
		$cNames{'floz'} = 'fluid ounce';
	$constants{'jig'} = parseExpr('3 tbsp'); # jigger
		$cNames{'jig'} = 'jigger';
	$constants{'gi'} = parseExpr('4 floz'); # US gill
		$cNames{'gi'} = 'US Gill';
	$constants{'cp'} = parseExpr('2 gi'); # US cup
		$cNames{'cp'} = 'US cup';
	$constants{'pt'} = parseExpr('2 cp'); # US pint
		$cNames{'pt'} = 'US pint';
	$constants{'qt'} = parseExpr('2 pt'); # US quart
		$cNames{'qt'} = 'US quart';
	$constants{'gal'} = parseExpr('4 qt'); # US gallon
		$cNames{'gal'} = 'US gallon';
	$constants{'bbl'} = parseExpr('31.5 gal'); # barrel
		$cNames{'bbl'} = 'barrel';
	$constants{'hogshead'} = parseExpr('63 gal'); 
		$cNames{'hogshead'} = 'hogshead';
	# volume (solid)
	$constants{'dry_pt'} = parseExpr('0.5506105 l'); 
		$cNames{'dry_pt'} = 'dry pint';
	$constants{'dry_qt'} = parseExpr('2 dry_pt'); 
		$cNames{'dry_qt'} = 'dry quart';
	$constants{'dry_gal'} = parseExpr('4 dry_qt'); 
		$cNames{'dry_gal'} = 'dry gallon';
	$constants{'peck'} = parseExpr('2 dry_gal'); 
		$cNames{'peck'} = 'peck';
	$constants{'bu'} = parseExpr('4 peck'); # bushel
		$cNames{'bu'} = 'bushel';
	$constants{'dry_bbl'} = parseExpr('3.281 bu'); # dry barrel
		$cNames{'dry_bbl'} = 'dry barrel';
	# time
	$constants{'min'} = parseExpr('60 s');
		$cNames{'min'} = 'minute';
	$constants{'hr'} = parseExpr('60 min');
		$cNames{'hr'} = 'hour';
	$constants{'day'} = parseExpr('24 hr');
		$cNames{'day'} = 'day';
	# mass (Avoirdupois, not Troy)
	$constants{'lb'} = parseExpr('453.592 g'); # pounds of mass
		$cNames{'lb'} = 'pounds of mass';
	$constants{'gr'} = parseExpr('lb/7000'); # grain
		$cNames{'gr'} = 'grain';
	$constants{'dr'} = parseExpr('(27 + 11/32) gr'); # dram 
		$cNames{'dr'} = 'dram';
	$constants{'oz'} = parseExpr('16 dr'); # ounce 
		$cNames{'oz'} = 'ounce';
	$constants{'cwt'} = parseExpr('100 lb'); # US hundredweight 
		$cNames{'cwt'} = 'US hundredweight';
	$constants{'ton'} = parseExpr('20 cwt'); # US ton (short ton) 
		$cNames{'ton'} = 'US ton (short ton)';
	$constants{'stone'} = parseExpr('14 lb'); # British/Irish stone (not Chinese)
		$cNames{'stone'} = 'British/Irish stone';
	# force
	$constants{'lbF'} = parseExpr('4.44822 N'); # pounds of force
		$cNames{'lbF'} = 'pounds of force';
	$constants{'slug'} = parseExpr('lbF s^2/ft'); # mass, Imperial
		$cNames{'slug'} = 'slug';
	# temperature
	$constants{'degF'} = parseExpr('5 K / 9'); # Δ degrees Fahrenheit
		$cNames{'degF'} = 'Δ degrees Fahrenheit';
	# energy
	$constants{'Btu'} = parseExpr('1055.05585 J'); # British thermal
		$cNames{'Btu'} = 'British thermal unit';
	$constants{'cal'} = parseExpr('4.184090 J'); # calories
		$cNames{'cal'} = 'calorie';
	# power
	$constants{'hp'} = parseExpr('745.699872 W'); # horsepower
		$cNames{'hp'} = 'horsepower';
	# insulation
	$constants{'Rvalue_US'} = parseExpr('ft^2 degF hr /Btu'); 
		$cNames{'Rvalue_US'} = 'US R value';
} # addEnglishUnits

sub addRussianUnits {
	# http://en.wikipedia.org/wiki/Obsolete_Russian_weights_and_measures
	# mass
	$constants{'funt'} = parseExpr('409.51718 g'); # фунт
		$cNames{'funt'} = 'фунт';
	$constants{'dolia'} = parseExpr('funt * 1/9216'); # до́ля 
		$cNames{'dolia'} = 'до́ля';
	$constants{'zolotnik'} = parseExpr('funt * 1/96'); # золотни́к 
		$cNames{'zolotnik'} = 'золотни́к';
	$constants{'lot'} = parseExpr('funt * 1/32'); # лот 
		$cNames{'lot'} = 'лот';
	$constants{'pood'} = parseExpr('funt * 40'); # пуд 
		$cNames{'pood'} = 'пуд';
	$constants{'berkovets'} = parseExpr('funt * 400'); # берковец 
		$cNames{'berkovets'} = 'берковец';
	# distance 
	$constants{'tochka'} = parseExpr('in / 100'); # то́чка
		$cNames{'tochka'} = 'то́чка';
	$constants{'liniya'} = parseExpr('in / 10'); # ли́ния
		$cNames{'liniya'} = 'ли́ния';
	$constants{'duiym'} = parseExpr('in'); # дюйм
		$cNames{'duiym'} = 'дюйм';
	$constants{'vershok'} = parseExpr('1.75 in'); # вершо́к
		$cNames{'vershok'} = 'вершо́к';
	$constants{'piad'} = parseExpr('7 in'); # пядь
		$cNames{'piad'} = 'пядь';
	$constants{'fut'} = parseExpr('ft'); # фут
		$cNames{'fut'} = 'фут';
	$constants{'arshin'} = parseExpr('7 ft / 3'); # арши́н
		$cNames{'arshin'} = 'арши́н';
	$constants{'sazhen'} = parseExpr('7 ft'); # са́жень
		$cNames{'sazhen'} = 'са́жень';
	$constants{'versta'} = parseExpr('3500 ft'); # верста́
		$cNames{'versta'} = 'верста́';
	$constants{'milia'} = parseExpr('24500 ft'); # ми́ля
		$cNames{'milia'} = 'ми́ля';
	# area
	$constants{'desiatina'} = parseExpr('2400 sazhen^2'); # десяти́на (treasury/official)
		$cNames{'desiatina'} = 'десяти́на';
		# proprietor's desiatina is 3200 sazhen^2
	# volume (solid)
	$constants{'garnets'} = parseExpr('3.279842 l'); # га́рнец
		$cNames{'garnets'} = 'га́рнец';
	$constants{'chast'} = parseExpr('garnets * 1/30'); # часть     
		$cNames{'chast'} = 'часть';
	$constants{'kruzhka'} = parseExpr('garnets * 2/5'); #  кру́жка    
		$cNames{'kruzhka'} = 'кру́жка';
	$constants{'vedro'} = parseExpr('garnets * 4'); #    ведро́     
		$cNames{'vedro'} = 'ведро́';
	$constants{'chetverik'} = parseExpr('garnets * 8'); #    четвери́к  
		$cNames{'chetverik'} = 'четвери́к';
	$constants{'osmina'} = parseExpr('garnets * 32'); #   осьми́на   
		$cNames{'osmina'} = 'осьми́на';
	$constants{'chetvert'} = parseExpr('garnets * 64'); #   че́тверть  
		$cNames{'chetvert'} = 'че́тверть';
	# volume (liquid)
	$constants{'vedro'} = parseExpr('12.29941 l'); # ведро́
		$cNames{'vedro'} = 'ведро́';
	$constants{'shkalik'} = parseExpr('vedro * 1/200'); # шка́лик 
		$cNames{'shkalik'} = 'шка́лик';
	$constants{'charka'} = parseExpr('vedro * 1/100'); # ча́рка 
		$cNames{'charka'} = 'ча́рка';
	$constants{'butylka_vodochnaya'} = parseExpr('vedro * 1/20'); # буты́лка_во́дочная
		$cNames{'butylka_vodochnaya'} = 'буты́лка_во́дочная';
	$constants{'butylka_vinnaya'} = parseExpr('vedro * 1/16'); # буты́лка_ви́нная 
		$cNames{'butylka_vinnaya'} = 'буты́лка_ви́нная';
	$constants{'kruzhka'} = parseExpr('vedro * 1/10'); # кру́жка 
		$cNames{'kruzhka'} = 'кру́жка';
	$constants{'shtof'} = parseExpr('vedro * 1/10'); # штоф 
		$cNames{'shtof'} = 'штоф';
	$constants{'bochka'} = parseExpr('vedro * 40'); # бо́чка 
		$cNames{'bochka'} = 'бо́чка';
	# there are other units as well
} # addRussianUnits

#Ronnel Turner
#Creates the arrays that holds the units for each drop down category
sub Dimensions{ 
        foreach my $key (keys %constants)
        {
                my $value = $constants{$key};
                my $val = ${$value}[0];
		#Checks if current unit is equal to base unit of that categroy
		#m
                if(isSameDim($value,$constants{"m"})){
                        push @length, $key;
                }
		#m^2
                elsif(isSameDim($value,$constants{"acre"})){
                        push @area, $key;
                }
		#kg
		elsif(isSameDim($value,$constants{"g"})){
                        push @mass, $key;
                }
		#m^3
                elsif(isSameDim($value,$constants{"pt"})){
                        push @volume, $key;
                }
		#m/s
                elsif(isSameDim($value,$constants{"c"})){
                        push @velocity ,$key;
                }
                elsif(isSameDim($value,$constants{"J"})){
                        push @energy, $key;
                }
		#s
                elsif(isSameDim($value,$constants{"s"})){
                        push @time, $key;
                }
		#currnecy
		elsif(isSameDim($value,$constants{"USD"})){
			push @dollar, $key;
		}
		#kg*m/(s^2)
                elsif(isSameDim($value,$constants{"N"})){
                        push @force, $key
                }
		#any that doesn't hit in the above cateogries
                else{
                        push @misc, $key;
                }
	}

	push @velocity, "m/s";
        push @velocity, "mi/hr";
        push @velocity, "nmi/hr";
        push @velocity, "km/hr";
        push @velocity, "ft/s";
	
}

#Ronnel Turner
#gets the array for the chosen drop down category
sub getUnits{
        my $u = $_[0];
        my @dimarray;
        my @tkey;
        my @tval;

        if($u eq "Length"){@dimarray = @length;}
	elsif($u eq "Mass") {@dimarray = @mass;}
        elsif($u eq "Area") {@dimarray = @area;}
        elsif($u eq "Volume") {@dimarray = @volume;}
        elsif($u eq "Energy") {@dimarray = @energy;}
        elsif($u eq "Time") {@dimarray = @time;}
        elsif($u eq "Force") {@dimarray = @force;}
        elsif($u eq "Velocity") {@dimarray = @velocity;}
        elsif($u eq "Dollars") {@dimarray = @dollar;}
        elsif($u eq "Misc") {@dimarray = @misc;}

        @tkey  = sort { lc($a) cmp lc($b) } @dimarray;

        return (@tkey);
}

sub showConstants {
	print "<pre>Known constants\n";
	for my $key (sort keys %constants) {
		printVal "\t$key: ", $constants{$key};
		print "  ($cNames{$key})\n";
	}
	print "</pre>";
} # showConstants

sub showVariables {
	print "<pre>Known variables\n";
	for my $key (sort keys %variables) {
		printVal "\t$key: ", $variables{$key};
		print "\n";
	}
	print "</pre>"
} # showVariables

#readevalPrint
#the main for the back end
#parses the input and returns an evaluation or error
sub readEvalPrint {
	my ($text) = @_;
	#loops through line of textarea
	for my $line (split(/\n/, $text)) {
		chomp $line;
		$line =~ s/%.*//; # comment
		next unless $line =~ /\w/;

		if ($line =~ /^\s*(\w+)\s*=(.*)/) { # assignment, use of equal sign
			my ($var, $value) = ($1, $2);
			$variables{$var} = parseExpr($value);
			printVal "$var = ", $variables{$var};
		} 
		elsif ($line =~ /^\s*convert\s+(.*)\s+to\s+(.*)/) {#converstion of a unit to another
			my ($orig, $new) = ($1, $2);
			my $result = parseExpr "(($orig) / ($new))";
			if (isScalar $result) {
				# $orig = "1 $orig" unless $orig =~ /^\d/;
				print "$orig = ", valToString($result) . " $new";
			} elsif (${$result}[0] eq 'NaN') {
				printVal ("" , $result);
			} else {
				print "Can't convert; different units.";
			}
		} elsif ($line =~ /^\s*addDim\s+(.*)\s+name\s+(.*)/) {

# Seifalla Moustafa; this else-if clause adds an element to the dimensions array 
# and inserts into the hash table a new entry containing the base unit 
# of the new dimension.

			my ($dim, $dimName) = ($1, $2);
			if (exists $constants {$dim}){
				print "Error: dimension already exists.";
			} else {
				my @dimPowers = ();
				my $length = scalar @{$constants {'s'}};
				push (@dimPowers, 1.0);
				foreach my $a (0 .. $length - 2) {
					push (@dimPowers, 0);
				}
				push (@dimPowers, 1);
				for my $constant (keys %constants) {
					push(@{$constants {$constant}}, 0);
				}
				push @names, $dim;
				push @{$zero}, 0;
				push @{$bad}, 0;
				push @{$constants{$dim}}, @dimPowers;
				push @{$cNames{$dim}}, $dimName;
			}
		}
		elsif ($line =~ /^\s*dimof\s+(.*)/) {

# Seifalla Moustafa; this else-if clause displays the dimensions of the input unit

                        my $dim = $1;
			my $result;
			if(!defined($variables{$dim})){
				$result = dimof(parseExpr($dim));
                        } else {
				$result = dimof(parseExpr($dim));
			}
			print "$dim : ", $result."";
                }else { # expression
			printVal "", parseExpr($line);
		}
		print "<br/>";
	}
} # readEvalPrint

init();
addSIUnits();
addPhysicsConstants();
addEnglishUnits();
addRussianUnits();
addCurrencies();
Dimensions();
doWork();
finalize();
