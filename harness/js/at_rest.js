// Finish CSS transitions, and keyframe fades, so a check reads colours at rest: Chrome reports
// a colour caught mid-transition in oklab(), a fade's start colour is not what the user is
// left with, and text still fading in would be skipped as transparent. Other keyframe
// animations keep running: a plugin's slideshow times its slides with one. An animation
// that cannot finish (endless, playback rate 0, or no end) is left as it is.
() => {
  const fades = (a) => a.effect?.getKeyframes().some((k) => "opacity" in k) &&
    a.effect.getComputedTiming().iterations !== Infinity;
  for (const a of document.getAnimations()) {
    if (!(a instanceof CSSTransition || (a instanceof CSSAnimation && fades(a)))) continue;
    try { a.finish(); } catch (e) { /* InvalidStateError: nothing to finish */ }
  }
}
