// Finish CSS transitions so a check reads colours at rest: Chrome reports a colour caught
// mid-transition in oklab(), and a fade's start colour is not what the user is left with.
// A transition that cannot finish (playback rate 0, or no end) is left as it is.
() => {
  for (const a of document.getAnimations()) {
    if (!(a instanceof CSSTransition)) continue;
    try { a.finish(); } catch (e) { /* InvalidStateError: nothing to finish */ }
  }
}
