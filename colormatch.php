<html>
<head>
<title>Find the Nearest Matching Color Name</title>

<?php
  function colorline($r, $g, $b, $name) {
    return "<tr><td>$name <td>($r $g $b) <td>" . colorswatch($r, $g, $b) . "\n";
  }
  function colorswatch($r, $g, $b) {
    return "<span style='background: rgb($r, $g, $b);'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>";
  }

function find_in_file($colorfile) {
  global $hex, $r, $g, $b;
  $nmatches = 0;
  $dist = 255 * sqrt(3.0);  # start with longest possible distance
  $fp = fopen($colorfile, 'r');
  if ($fp) {
    while (!feof($fp)) {
       $line = fgets($fp);
       if ($line[0] != '!') {
         list($r1, $g1, $b1, $name) = sscanf($line, "%d %d %d %s");
	 if ($r1 == $r && $g1 == $g && $b1 == $b) {
	   print(colorline($r1, $g1, $b1, $name));
	   ++$nmatches;
	   $dist == 0;
	 }
	 if ($nmatches == 0) {
	   # if no exact match yet, see if it's closer than what
	   # we've seen before.
	   $newdist = sqrt(pow($r-$r1, 2) + pow($g-$g1, 2) + pow($b-$b1, 2));
	   if ($newdist == $dist) {
	     $matches = $matches . colorline($r1, $g1, $b1, $name);
	   } else if ($newdist < $dist) {
	     $dist = $newdist;
	     $matches = colorline($r1, $g1, $b1, $name);
	   }
	 }
       }
    }
    fclose($fp);
    if ($nmatches == 0) {
      print("<tr>");
      print("<td colspan=2>No exact match found for ($r $g $b)\n<td>");
      print(colorswatch($r, $g, $b));
      print("<tr><th colspan=3>Closest matches:");
      print($matches);
    }
  }
}

  $hex = $_GET['hex'];
  # hex is a code like fff or 11aa77. Split it into r, g and b:
  $len = strlen($hex);
  if ($len == 3) {
    $r = hexdec($hex[0]); $r *= 17;
    $g = hexdec($hex[1]); $g *= 17;
    $b = hexdec($hex[2]); $b *= 17;
  }
  else if ($len == 6) {
    $r = hexdec(substr($hex, 0, 2));
    $g = hexdec(substr($hex, 2, 2));
    $b = hexdec(substr($hex, 4, 2));
  }
  else {
    $r = $_GET['r'];
    $g = $_GET['g'];
    $b = $_GET['b'];
  }
  $len = strlen($hex);
?>

</head>

<body>
<h1>Find the Nearest Matching Color Name</h1>

This page can take a three or six digit hexadecimal color specifier
(e.g. #fff or #a210f0), or three decimal numbers for red, green, and
blue, and find the nearest named colors, either in the Unix
<a href="http://www-swiss.ai.mit.edu/~jaffer/Color/rgb.txt">RGB.txt</a>
or in the much smaller set of
<a href="http://www.w3.org/TR/CSS21/syndata.html#color-units">CSS colors</a>.

<p>

<form method="GET" action="index.php">
Hex code (3 or 6 digits): #<input type=text name="hex" size=6>
<input type="submit" value="Match by hex code">
</form>
<p>
<form method="GET" action="index.php">
<p>
or Decimal values:
<p>
Red: <input type=text name="r" size=4>
Green: <input type=text name="g" size=4>
Blue: <input type=text name="b" size=4>
<input type="submit" value="Match by RGB values">
</form>

<?php
  if ($hex != "" || ($r != "" && $g != "" && $b != "")) {
    print ("<p>\n<hr>\n<p>\n<h2>Matches in rgb.txt:</h2>\n<table>\n");
    find_in_file ("/etc/X11/rgb.txt");
    print("</table>\n");

    print("<h2>Matches in CSS color list:</h2><table>\n");
    find_in_file ("csscolors.txt");
  }
?>
</table>

<p>
<a href="colormatch.php.txt">The source code.</a>

<hr>
<a href="/linux/">Linux links</a> ...
<a href="/">Shallow Sky home</a> ...
<i><a href="/mailme.html">...Akkana</a></i>


</body>
</html>
