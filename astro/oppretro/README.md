Someone asked me, "How did Kepler figure out when Mars was at opposition
without having access to accurate clocks?

I wondered if he might have taken the midpoint of its retrograde loop.
How close is that to the time of opposition? Neither of us knew.

So I wrote a program using PyEphem to calculate that. But along the
way, I hit a snag in PyEphem (which turned out to be merely something
missing in the documentation, easily fixed once I figured out what
it was doing) and wondered if PyEphem was obsolete and maybe I should
be using astropy. So I wrote a version in astropy.

Answer: No, stick with PyEphem. It's faster by a huge margin, and
it gets more or less the right answer where astropy doesn't (I'm still
not clear why not). Still, astropy may improve, and it's useful to
have an example of how to use it, so I've kept it.

It turns out the author of PyEphem has a new library out called
[SkyField](http://rhodesmill.org/skyfield/)
which is probably worth a look. I haven't tried it yet.

Oh, and if you're curious about the Kepler question? The PyEphem version
currently says (if I got my calculations right) that the retrograde
midpoint is roughly halfway between opposition and closest approach,
and the difference between opposition and the midpoint is about
32 arcmin (half a degree). Would that have been close enough to
help Kepler? I don't know. I'm passing the info on to my friend
who's doing research for a talk and will let him figure that out.
