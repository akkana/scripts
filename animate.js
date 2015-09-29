/*
 * Simple Javascript animation code. 
 */

/*
// appear() is from http://stackoverflow.com/a/2207751
// It's good for fading in one image
// but not for fading from one image to another.
// Want to adapt it to fade in each image while the preceding one
// is still visible, but that will require double buffering.
function appear(elm, i, step, speed){
    var t_o;
    //initial opacity
    i = i || 0;
    //opacity increment
    step = step || 5;
    //time waited between two opacity increments in msec
    speed = speed || 50; 

    t_o = setInterval(function(){
        //get opacity in decimals
        var opacity = i / 100;
        //set the next opacity step
        i = i + step; 
        if(opacity > 1 || opacity < 0){
            clearInterval(t_o);
            //if 1-opaque or 0-transparent, stop
            return; 
        }
        //modern browsers
        elm.style.opacity = opacity;
        //older IE
        elm.style.filter = 'alpha(opacity=' + opacity*100 + ')';
    }, speed);
}
 */

var image_index = 0;
var delay = 500;
var el;
var interval_id;
var running = false;

// Pause for this many beats on the last image:
var pause_at_end = 5;
var end_pause_count = pause_at_end;

function start_stop(images, el, newdelay) {
    if (running) {
        clearInterval(interval_id);
        running = false;
        return;
    }

    running = true;
    if (newdelay)
        delay = newdelay;
    interval_id = setInterval(function() {
        //el.style.opacity = 0;
        el.src = images[image_index];
        //appear(el, 0, 10, 200);

        if (image_index == images.length-1) {
            if (end_pause_count > 0) {
                end_pause_count--;
                return;
            }
            end_pause_count = pause_at_end;
        }

        image_index = (image_index+1) % images.length;

    }, delay)
}
