/* -*- Mode: Javascript; js-indent-level: 4; indent-tabs-mode: nil; -*- */

// Javascript code to calculate the position of Jupiter's moons and shadows.
// Copyright 2009, 2013 by Akkana Peck --
// please share and enjoy under the terms of the GPL v2 or later.
//
// Equations come from Jean Meeus, Astronomical Formulae for Calculators.

// Code below is from Jupiter.java and is in the process of being
// translated to javascript.


function Jupiter()
{
    const NUM_MOONS = 4;

    var curdate;        // javascript Date object
    var d;		// days since epoch, 1899 Dec 31 12h ET
    
    // Angles of each of the Galilean satellites, in radians,
    // expressed relative to each satellite's inferior conjunction:
    var moonAngles = [NaN, NaN, NaN, NaN];
    // And their distances from the planet:
    var moonDist = [NaN, NaN, NaN, NaN];

    // variables we may want later for moon calcs:
    var psi;
    
    var delta;	// Earth-Jupiter distance
    var De;		// planetocentric ang. dist. of earth from jup. equator
    var G;
    var H;

    // latitudes of systems I and II:
    var lambda1;
    var lambda2;

    function getDate() {
        return curdate;
    }
    this.getDate = getDate;

    //
    // Convert an angle (in radians) so that it's between 0 and 2*PI:
    //
    function angle(a)
    {
	if (a < 10000)
	    return oangle(a);
	a = a - 2.*Math.PI * parseInt(a / 2. / Math.PI);
	if (a < 0)
	    a += 2*Math.PI;
    	return a;
    }

    function oangle(a)
    {
        while (a > 2 * Math.PI)
            a -= 2. * Math.PI;
        while (a < 0)
            a += 2. * Math.PI;
        return a;
    }
    
    function setDate(initDate)
    {
        // Calculate the position of Jupiter's central meridian,
        // and the corresponding moonAngle and moonDist arrays;
        // and system I and system II longitudes;
        // psi, the Jupiter's phase angle (always btw. -12 and 12 degrees):
        // and De, the planetocentric angular distance of the earth
        // from the equator of Jupiter.

        // First, get the number of days since 1899 Dec 31 12h ET.
        curdate = initDate;
        var d = getJulianDate(initDate) - 2415020;     // days since 1899 Dec 31 12h ET

        // Argument for the long-period term in the motion of Jupiter:
        var V = angle((134.63 + .00111587 * d) * Math.PI / 180);
	
        // Mean anomalies of Earth and Jupiter:
        var M = angle((358.476 + .9856003 * d) * Math.PI / 180);
        var N = angle((225.328 + .0830853 * d + .33 * Math.sin(V))
			 * Math.PI / 180);
	
        // Diff between the mean heliocentric longitudes of Earth & Jupiter:
        var J = angle((221.647 + .9025179 * d - .33 * Math.sin(V))
			 * Math.PI / 180);
	
        // Equations of the center of Earth and Jupiter:
        var A = angle((1.916 * Math.sin(M) + .020 * Math.sin(2*M))
        	 	 * Math.PI / 180);
        var B = angle((5.552 * Math.sin(N) + .167 * Math.sin(2*N))
        		 * Math.PI / 180);
	
        var K = angle(J + A - B);
	
        // Distances are specified in AU:
        // Radius vector of the earth:
        var R = 1.00014 - .01672 * Math.cos(M) - .00014 * Math.cos(2*M);
        // Radius vector of Jupiter:
        var r = 5.20867 - .25192 * Math.cos(N) - .00610 * Math.cos(2*N);
	
        // Earth-Jupiter distance:
        delta = Math.sqrt(r*r + R*R - 2*r*R*Math.cos(K));
	
        // Phase angle of Jupiter (always btw. -12 and 12 degrees):
        psi = Math.asin(R / delta * Math.sin(K));
	
	// Longitude of system 1:
        lambda1 = angle((268.28 * 877.8169088 * (d - delta / 173))
			* Math.PI / 180 + psi - B);
        // Longitude of system 2:
        lambda2 = angle((290.28 + 870.1869088 * (d - delta / 173))
			 * Math.PI / 180 + psi - B);

        // calculate the angles of each of the satellites:
        moonAngles[0] = angle((84.5506 + 203.4058630 * (d - delta / 173))
			      * Math.PI / 180
			      + psi - B);
        moonAngles[1] = angle((41.5015 + 101.2916323 * (d - delta / 173))
			      * Math.PI / 180
			      + psi - B);
	moonAngles[2] = angle((109.9770 + 50.2345169 * (d - delta / 173))
			      * Math.PI / 180
			      + psi - B);
        moonAngles[3] = oangle((176.3586 + 21.4879802 * (d - delta / 173))
			      * Math.PI / 180
			      + psi - B);
	
        // and the planetocentric angular distance of the earth
        // from the equator of Jupiter:
        var lambda = angle((238.05 + .083091 * d + .33 * Math.sin(V))
                              * Math.PI / 180 + B);

        De = ((3.07 * Math.sin(lambda + 44.5 * Math.PI / 180)
	       - 2.15 * Math.sin(psi) * Math.cos(lambda - 24.*Math.PI/180)
	       - 1.31 * (r - delta) / delta
	       * Math.sin(lambda - 99.4 * Math.PI / 180))
	      * Math.PI / 180);
	
	G = angle((187.3 + 50.310674 * (d - delta / 173)) * Math.PI / 180);
	H = angle((311.1 + 21.569229 * (d - delta / 173)) * Math.PI / 180);

	// Calculate the distances before any corrections are applied:
	moonDist[0] = 5.9061 -
		       .0244 * Math.cos(2 * (moonAngles[0] - moonAngles[1]));
        moonDist[1] = 9.3972 -
		       .0889 * Math.cos(2 * (moonAngles[1] - moonAngles[2]));
	moonDist[2] = 14.9894 - .0227 * Math.cos(G);
	moonDist[3] = 26.3649 - .1944 * Math.cos(H);
	
        // apply some first-order correction terms to the angles:
    	moonAngles[0] = angle(moonAngles[0] +
			      Math.sin(2 * (moonAngles[0] - moonAngles[1]))
			      * .472 * Math.PI / 180);
    	moonAngles[1] = angle(moonAngles[1] +
			      Math.sin(2 * (moonAngles[1] - moonAngles[2]))
			      * 1.073 * Math.PI / 180);
       	moonAngles[2] = angle(moonAngles[2] +
			      Math.sin(G) * .174 * Math.PI / 180);
    	moonAngles[3] = angle(moonAngles[3] +
			      Math.sin(H) * .845 * Math.PI / 180);
    }
    /* Make the function public: */
    this.setDate = setDate;

    function daysBetween(d1, d2) {
        return ((d2.getTime() - d1.getTime())) / (24.*60.*60.*1000.);
    }

    function getJulianDate(d) {
        return (daysBetween(new Date("Jan 1 0:00 PST 1970"), d)
		+ 2440587.83333333333);
    }

    /* object that has .x and .y */
    function XYCoord(x, y) {
        this.x = x || NaN;
        this.y = y || NaN;
    }
    
    //
    // Returns the moon position in units of Jupiter radii.
    // Also calculate the shadows, and whether the moon is eclipsed
    // by Jupiter's shadow or transiting in front of Jupiter.
    //
    function getMoonXYData(whichmoon)
    {
	var r = moonDist[whichmoon];
	
        var moondata = new Object();

        function getShadowXY(angle)
        {
            var moonSunAngle = angle - psi;
    	    var xy = new XYCoord();
            xy.x = r * Math.sin(moonSunAngle);
            xy.y = r * Math.cos(moonSunAngle) * Math.sin(De);
            return xy;
        }

	moondata.moonx = r * Math.sin(moonAngles[whichmoon]);
	moondata.moony = r * Math.cos(moonAngles[whichmoon]) * Math.sin(De);

        // Is the moon directly in front of or behind Jupiter's disk?
        // Then this distance will be <= 1.
        diskdist = dist(moondata.moonx, moondata.moony);

        s = "moon " + whichmoon;
        s += "\nDist = " + r;
        s += "\nmoonAngle = " + moonAngles[whichmoon];
        s += " = " + moonAngles[whichmoon] * 180. / Math.PI;
        s += "\nJup phase angle = " + psi;
        s += " = " + psi * 180. / Math.PI;

	// See whether the moon is on the near side of the planet:
        if (moonAngles[whichmoon] < Math.PI * .5
	    || moonAngles[whichmoon] > Math.PI * 1.5)
        {
            // Is it transiting? Leave a little slop, consider a moon
            // transiting when it's just starting its transit.
            if (diskdist < .9)
                moondata.transit = true;

            // Since the moon is on the near side, check for shadows
            // cast by the moon on the planet.
            s += "\nNear side of the planet";
            moondata.farside = false;

            xy = getShadowXY(moonAngles[whichmoon]);
            moondata.shadowx = xy.x;
            moondata.shadowy = xy.y;

            // Is it hitting the planet? If not, set coords to NaN.
            // Some day, ought to check for moons eclipsing other moons
            if (moondata.shadowx < -1. || moondata.shadowx > 1.)
                moondata.shadowx = moondata.shadowy = NaN;
        }

        // Is the moon blocked by the planet, so it's invisible?
        //else if (moondata.moonx < 1. && moondata.moonx > -1.)
        else if (diskdist < 1.0)
	{
            moondata.farside = true;
	    moondata.moonx = moondata.moony = NaN;
            s += "\nBlocked by the planet";
	}

        // Otherwise, it's on the far side.
        // See if it's eclipsed by the planet's shadow.
        else {
            moondata.farside = true;
            s += "\nFar side of the planet";

            // See if a moon 180 degrees away from this moon's position,
            // at the same distance, would cast a shadow on the planet.
            // If so, the actual moon is eclipsed.
            //atmoslop = 1.0;   // .83 might be worth pursuing
            atmoslop = .9;
            xy = getShadowXY(angle(moonAngles[whichmoon] + Math.PI));
            moondata.eclipse = (dist(xy.x, xy.y) < atmoslop);
            s += "\nActual moon at (" + moondata.moonx + ", " + moondata.moony + ")";
            s += "\nFake shadow at (" + xy.x + ", " + xy.y + ")";
            s += "\nDist from center = " + Math.sqrt(xy.x*xy.x + xy.y*xy.y);
            if (moondata.eclipse)
                s += "\nEclipse of moon " + whichmoon + "!";
        }

        //if (moondata.eclipse) alert(s);
    	return moondata;
    }
    this.getMoonXYData = getMoonXYData
    
    //
    // The Great Red Spot, currently at longitude 61 in system II
    //
    function getRedSpotXY(spot_in_deg)
    {
	var spotlong = angle(lambda2 - spot_in_deg*Math.PI/180);
	
    	var coord = new XYCoord();

	// See if the spot is visible:
	if (spotlong > Math.PI * .5 && spotlong < Math.PI * 1.5) {
	    coord.x = coord.y = NaN;
	} else {
	    coord.x = Math.sin(spotlong);
	    coord.y = .42;	// completely random wild-assed guess
	}
	
    	return coord;
    }
    this.getRedSpotXY = getRedSpotXY;

    //
    // You might also want to get the location of some arbitrary
    // other position on the planet, e.g. the Great Northern Spot.
    //
    function getJovianPointX(long_in_deg, systm)
    {
	var lambda = (systm == 1 ? lambda1 : lambda2);
        var longInRad = angle(lambda - long_in_deg*Math.PI/180);

	// See if the point is visible:
	if (longInRad > Math.PI * .5 && longInRad < Math.PI * 1.5) {
	    return NaN;
	} else {
	    return Math.sin(longInRad);
	}
    }
}

function dist(x, y)
{
    return Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2));
}

function prettytime(tothrs)
{
    if (tothrs < 24)
        pt = tothrs + " hours";
    else {
        hrs = tothrs % 24;
        days = (tothrs-hrs) / 24;
        pt = days + " day";
        if (days != 1)
            pt += "s";

        if (hrs == 1)
            pt += ", 1 hour";
        else if (hrs > 0)
            pt += ", " + hrs + " hours";
    }
    return pt;
}

//
// Build a table of upcoming moon events for a given interval.
//
function upcomingEvents(date, tothrs)
{
    var saveDate = jup.curdate;
    if (!saveDate) {
        saveDate = date;
    }

    interval = 1;   // minutes
    upcoming = "<b>Moon events in the next " + prettytime(tothrs) + "</b>\n\n";

    moonnames = [ "Io", "Europa", "Ganymede", "Callisto" ];

    d = new Date(date);
    lastmoondata  = [ null, null, null, null ];
    // Moon data includes moonx, moony, shadowx, shadowy, farside, and eclipsed.

    var verbose = false;

    for (mins = -30; mins < tothrs * 60; mins += interval) {
        d.setTime(date.getTime() + mins * 60 * 1000);
        jup.setDate(d);
        if (verbose)
            upcoming += "\n" + d + "\n";

        // Keep track of how many moons are involved in events
        nshadows = 0;
        ntransits = 0;

        thisevent = "";
        for (var whichmoon = 0; whichmoon < 4; ++whichmoon) {
            moondata = jup.getMoonXYData(whichmoon);
            if (verbose) {
                upcoming += " (" + whichmoon + "):\n";
                upcoming += JSON.stringify(moondata) + "\n";
            }

            if (lastmoondata[whichmoon]) {
                // Count total events
                if (moondata.shadowx)
                    ++nshadows;
                if (moondata.transit)
                    ++ntransits;

                if (!moondata.moonx && lastmoondata[whichmoon].moonx)
                    thisevent += d + ": "
                                + moonnames[whichmoon] + " disappears\n";
                else if (moondata.moonx && ! lastmoondata[whichmoon].moonx) {
                    if (! moondata.eclipse)
                        thisevent += d + ": "
                                    + moonnames[whichmoon] + " reappears\n";
                }

                else if (moondata.transit && ! lastmoondata[whichmoon].transit)
                    thisevent += d + ": " + moonnames[whichmoon]
                                + " begins transit\n";
                else if (! moondata.transit && lastmoondata[whichmoon].transit)
                    thisevent += d + ": " + moonnames[whichmoon]
                                + " ends transit\n";

                else if (moondata.eclipse && ! lastmoondata[whichmoon].eclipse)
                    thisevent += d + ": " + moonnames[whichmoon]
                                + " enters eclipse\n";
                else if (! moondata.eclipse && lastmoondata[whichmoon].eclipse)
                    thisevent += d + ": " + moonnames[whichmoon]
                                + " leaves eclipse\n";

                if (!moondata.shadowx && lastmoondata[whichmoon].shadowx)
                    thisevent += d + ": " + moonnames[whichmoon]
                                + "'s shadow disappears\n";
                else if (moondata.shadowx && !lastmoondata[whichmoon].shadowx)
                    thisevent += d + ": " + moonnames[whichmoon]
                                + "'s shadow appears\n";

                //if (verbose)
                //    upcoming += JSON.stringify(lastmoondata[whichmoon]) + "\n"
            }

            // Ick! This is supposedly the most efficient way to clone
            // an object in javascript. Can you believe it?
            lastmoondata[whichmoon] = JSON.parse(JSON.stringify(moondata));
        } // end loop over whichmoon

        if (thisevent && (nshadows + ntransits > 1))
            upcoming += "<b>" + pluralize(ntransits, "transit")
                       + ", " + pluralize(nshadows, "shadow") + ":</b>\n";
        upcoming += thisevent;
    }

    if (saveDate != undefined)
        jup.setDate(saveDate);
    return upcoming;
}

function endsWith(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1;
}

function pluralize(num, word)
{
    if (num == 1)
        return "1 " + word;
    else if (endsWith(word, 's'))
        return num + " " + word + "es";
    return num + " " + word + "s";
}
