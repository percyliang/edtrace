/**
 * Navigates to a new URL with updated URL parameters (`urlParams + delta`).
 */
export function navigateToUrl(urlParams, delta, location, navigate) {
  for (const key in delta) {
    if (delta[key] === null || delta[key] === false) {
      urlParams.delete(key);
    } else {
      urlParams.set(key, delta[key]);
    }
  }
  navigate({
    pathname: location.pathname,
    search: urlParams.toString(),
  });
}

/**
 * Returns the last element of an array.
 */
export function getLast(arr) {
  return arr[arr.length - 1];
}