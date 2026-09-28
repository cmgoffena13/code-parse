function callee() {
  return 1;
}

function caller() {
  callee(); callee();
}
