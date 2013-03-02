// Javascript code to calculate the position of Jupiter's moons and shadows.
// Copyright 2009 by Akkana Peck --
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

    function daysBetween(d1, d2)
    {
        return ((d2.getTime() - d1.getTime())) / (24.*60.*60.*1000.);
    }

    function getJulianDate(d) {
        return ( daysBetween(new Date("Jan 1 0:00 PST 1970"), d)
		+ 2440587.83333333333);
    }

    /* object that has .x and .y */
    function XYCoord(x, y) {
        this.x = x || NaN;
        this.y = y || NaN;
    }
    
    //
    // Returns the moon position in units of Jupiter radii.
    // Also calculate the shadows, and whether the moon is eclipsed by Jupiter.
    //
    function getMoonXYData(whichmoon)
    {
	var r = moonDist[whichmoon];
	
    	//var mooncoord = new XYCoord();
        var moondata = new Object();

	moondata.moonx = r * Math.sin(moonAngles[whichmoon]);
	moondata.moony = r * Math.cos(moonAngles[whichmoon]) * Math.sin(De);

        s = "moon " + whichmoon;
        s += "\nDist = " + r;
        s += "\nmoonAngle = " + moonAngles[whichmoon];

	// See whether the moon is on the far side of the planet:
        if (moonAngles[whichmoon] > Math.PI * .5
	    && moonAngles[whichmoon] < Math.PI * 1.5)
        {
            s += "\nFar side of the planet";
            moondata.farside = true;

            // Is the moon blocked by the planet, so it's invisible?
	    if (moondata.moonx < 1. && moondata.moonx > -1.)
	    {
	        moondata.moonx = moondata.moony = NaN;
                s += "\nBlocked by the planet";
	    }
            else {
                // if not, then figure out whether the planet's shadow
                // might be eclipsing the moon.
                // Calculate the moon-planet-sun angle:
	        var moonSunAngle = moonAngles[whichmoon] - psi;
                s += "\nMSA = " + moonSunAngle;
                moondata.eclipse = (1. < r * Math.sin(moonSunAngle))
                if (moondata.eclipse) {
                    s += "Eclipse of moon " + whichmoon + "!";
                }
            }
        }

        // Since the moon is on the near side, check for shadows
        // cast by the moon on the planet.
        else {
            s += "\nNear side of the planet";
            moondata.farside = false;

            // Calculate the moon-planet-sun angle:
	    var moonSunAngle = moonAngles[whichmoon] - psi;

            moondata.shadowx = r * Math.sin(moonSunAngle);
            // This Y coord isn't right ... need to derive the right eqn:
            moondata.shadowy = r * Math.cos(moonSunAngle) * Math.sin(De);

            // Is it hitting the planet? If not, set coords to NaN.
            // Some day, ought to check for moons eclipsing other moons
            if (moondata.shadowx < -1. || moondata.shadowx > 1.)
                moondata.shadowx = moondata.shadowy = NaN;
        }

        //if (whichmoon == 1) alert(s);
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

