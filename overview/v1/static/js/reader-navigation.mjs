/* Retained Work, Map, Calendar, and Timeline routes may be reader return
 * destinations. Keep the original query/hash bytes; URL normalization must
 * not broaden trust.
 */
export function safeReturnTo(value) {
  if (typeof value !== 'string' || !/^\/(?:work|map|calendar|timeline|projects)\/?(?:[?#]|$)/.test(value) ||
      /[\\\x00-\x20\x7f]/.test(value)) return '/work';
  try {
    const url = new URL(value, 'https://navigation.invalid');
    if (url.origin !== 'https://navigation.invalid' ||
        !['/work', '/work/', '/map', '/map/', '/calendar', '/calendar/', '/timeline', '/timeline/', '/projects', '/projects/'].includes(url.pathname)) return '/work';
    return value;
  } catch { return '/work'; }
}

export function readerHref(href, context = location) {
  if (typeof href !== 'string' || !href.startsWith('/work-order?')) return href;
  const url = new URL(href, 'https://navigation.invalid');
  url.searchParams.set('return_to', safeReturnTo(context.pathname + context.search + context.hash));
  return url.pathname + url.search + url.hash;
}
