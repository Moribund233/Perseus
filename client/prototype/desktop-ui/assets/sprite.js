/* 品牌Logo + 最小占位图标（正式实现沿用 web 端 @ant-design/icons 体系） */
(function () {
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">' +
    '<symbol id="i-logo" viewBox="0 0 120 120">' +
      '<path d="M43.9 46.1 A24 24 0 0 1 69.9 67.9" fill="none" stroke="#3D7BFF" stroke-width="9" stroke-linecap="round"/>' +
      '<path d="M39.7 34.5 A36 36 0 0 1 81.9 73.1" fill="none" stroke="#3D7BFF" stroke-width="9" stroke-linecap="round"/>' +
      '<path d="M62.4 24.9 A48 48 0 0 1 92.4 57.6" fill="none" stroke="#12A38B" stroke-width="9" stroke-linecap="round"/>' +
      '<path d="M37.8 92.6 A24 24 0 0 1 23.4 78.2" fill="none" stroke="#E9F1FF" stroke-width="8" stroke-linecap="round"/>' +
      '<circle cx="46" cy="70" r="11" fill="#3D7BFF"/><circle cx="10" cy="73" r="4.5" fill="#12A38B"/>' +
    '</symbol>' +
    '<symbol id="i-folder" viewBox="0 0 24 24"><path d="M3.5 7a2 2 0 0 1 2-2h4.2l2 2h9.3v10.5a2 2 0 0 1-2 2h-13.5a2 2 0 0 1-2-2z"/></symbol>' +
    '<symbol id="i-file" viewBox="0 0 24 24"><path d="M6.5 3.5h7l4.5 4.5v12.5h-11.5z"/><path d="M13.5 3.5V8H18"/></symbol>' +
    '<symbol id="i-chev-r" viewBox="0 0 24 24"><path d="M9.5 6.5l6 5.5-6 5.5"/></symbol>' +
    '<symbol id="i-x" viewBox="0 0 24 24"><path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/></symbol>' +
    '<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5.5v13M5.5 12h13"/></symbol>' +
    '<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.2"/><path d="M15.6 15.6L20.5 20.5"/></symbol>' +
    '<symbol id="i-branch" viewBox="0 0 24 24"><circle cx="7" cy="6.5" r="2.1"/><circle cx="7" cy="17.5" r="2.1"/><circle cx="17" cy="6.5" r="2.1"/><path d="M7 8.6v6.8M17 8.6c0 3-3 3.6-5.6 3.9"/></symbol>' +
    '<symbol id="i-commit" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.2"/><path d="M3 12h5.8M15.2 12H21"/></symbol>' +
    '<symbol id="i-arrow-l" viewBox="0 0 24 24"><path d="M19 12H5.5M11 6l-6 6 6 6"/></symbol>' +
    '<symbol id="i-star" viewBox="0 0 24 24"><path d="M12 4l2.4 5.2 5.6.6-4.2 3.8 1.2 5.6-5-2.9-5 2.9 1.2-5.6L4 9.8l5.6-.6z"/></symbol>' +
    '<symbol id="i-fork" viewBox="0 0 24 24"><circle cx="7" cy="6" r="2.1"/><circle cx="17" cy="6" r="2.1"/><circle cx="12" cy="18" r="2.1"/><path d="M7 8.1V9a3 3 0 0 0 3 3h4a3 3 0 0 0 3-3v-.9M12 12v3.9"/></symbol>' +
    '<symbol id="i-download" viewBox="0 0 24 24"><path d="M12 4.5v10M7.5 10.5l4.5 4.5 4.5-4.5M5 19.5h14"/></symbol>' +
    '<symbol id="i-check" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></symbol>' +
    '<symbol id="i-check-c" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><path d="M8.5 12.3l2.4 2.4 4.6-5"/></symbol>' +
    '<symbol id="i-warn" viewBox="0 0 24 24"><path d="M12 4.2L2.8 19.5h18.4z"/><path d="M12 10v4.2M12 16.8v.4"/></symbol>' +
    '<symbol id="i-err" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><path d="M9.2 9.2l5.6 5.6M14.8 9.2l-5.6 5.6"/></symbol>' +
    '<symbol id="i-bell" viewBox="0 0 24 24"><path d="M6.5 16.5v-5a5.5 5.5 0 0 1 11 0v5l1.6 2.2H4.9z"/><path d="M10 20.5a2.1 2.1 0 0 0 4 0"/></symbol>' +
    '<symbol id="i-gear" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.1"/><path d="M12 3v2.6M12 18.4V21M3 12h2.6M18.4 12H21M5.6 5.6l1.9 1.9M16.5 16.5l1.9 1.9M18.4 5.6l-1.9 1.9M7.5 16.5l-1.9 1.9"/></symbol>' +
    '<symbol id="i-server" viewBox="0 0 24 24"><rect x="4" y="4.5" width="16" height="6" rx="1.6"/><rect x="4" y="13.5" width="16" height="6" rx="1.6"/><path d="M7.4 7.5h.1M7.4 16.5h.1"/></symbol>' +
    '<symbol id="i-refresh" viewBox="0 0 24 24"><path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 3.8v3.4h-3.4"/></symbol>' +
    '<symbol id="i-edit" viewBox="0 0 24 24"><path d="M4.5 19.5h4L19.6 8.4a2 2 0 0 0 0-2.8l-1.2-1.2a2 2 0 0 0-2.8 0L4.5 15.5z"/></symbol>' +
    '<symbol id="i-trash" viewBox="0 0 24 24"><path d="M5 7h14M9.5 7V4.8h5V7M6.8 7l.9 12.4h8.6L17.2 7M10.2 10.5v5.5M13.8 10.5v5.5"/></symbol>' +
    '<symbol id="i-list" viewBox="0 0 24 24"><path d="M9 6.5h11M9 12h11M9 17.5h11"/><circle cx="5" cy="6.5" r=".9"/><circle cx="5" cy="12" r=".9"/><circle cx="5" cy="17.5" r=".9"/></symbol>' +
    '<symbol id="i-grid" viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="1.4"/><rect x="13" y="4" width="7" height="7" rx="1.4"/><rect x="4" y="13" width="7" height="7" rx="1.4"/><rect x="13" y="13" width="7" height="7" rx="1.4"/></symbol>' +
    '<symbol id="i-msg" viewBox="0 0 24 24"><path d="M4.5 6h15v10h-9l-4.5 3.6V6z"/></symbol>' +
    '<symbol id="i-eye" viewBox="0 0 24 24"><path d="M2.8 12s3.5-6 9.2-6 9.2 6 9.2 6-3.5 6-9.2 6S2.8 12 2.8 12z"/><circle cx="12" cy="12" r="2.6"/></symbol>' +
    '<symbol id="i-merge" viewBox="0 0 24 24"><circle cx="7" cy="6" r="2.1"/><circle cx="7" cy="18" r="2.1"/><circle cx="17" cy="12" r="2.1"/><path d="M7 8.1v7.8M8.9 6.5c4.5.4 6.4 2.2 6.7 4"/></symbol>' +
    '<symbol id="i-send" viewBox="0 0 24 24"><path d="M20.5 3.5L10.8 13.2M20.5 3.5l-6.2 17-3.5-7.3-7.3-3.5z"/></symbol>' +
    '<symbol id="i-terminal" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="1.8"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15H17"/></symbol>' +
    '<symbol id="i-panel-b" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="1.8"/><path d="M3.5 14.5h17"/></symbol>' +
    '<symbol id="i-panel-r" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="1.8"/><path d="M14.5 4.5v15"/></symbol>' +
    '<symbol id="i-user" viewBox="0 0 24 24"><circle cx="12" cy="8.2" r="3.6"/><path d="M5 20c1.4-3.6 4-5.2 7-5.2s5.6 1.6 7 5.2"/></symbol>' +
    '<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><path d="M12 7.5V12l3 2"/></symbol>' +
    '<symbol id="i-copy" viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a1.5 1.5 0 0 1 1.5-1.5H15"/></symbol>' +
    '<symbol id="i-more" viewBox="0 0 24 24"><circle cx="5.5" cy="12" r="1.1"/><circle cx="12" cy="12" r="1.1"/><circle cx="18.5" cy="12" r="1.1"/></symbol>' +
    '<symbol id="i-min" viewBox="0 0 24 24"><path d="M6 12h12"/></symbol>' +
    '<symbol id="i-max" viewBox="0 0 24 24"><rect x="6.5" y="6.5" width="11" height="11" rx="1.2"/></symbol>' +
    '<symbol id="i-up" viewBox="0 0 24 24"><path d="M12 19V5.5M6.5 11L12 5.5 17.5 11"/></symbol>' +
    '<symbol id="i-down" viewBox="0 0 24 24"><path d="M12 5v13.5M6.5 13L12 18.5 17.5 13"/></symbol>' +
    '<symbol id="i-zap" viewBox="0 0 24 24"><path d="M13 3.5L5.5 13.5h5l-1 7 7.5-10h-5z"/></symbol>' +
    '<symbol id="i-plug" viewBox="0 0 24 24"><path d="M9 3.5V9M15 3.5V9M7 9h10v3a5 5 0 0 1-10 0zM12 17v3.5"/></symbol>' +
    '<symbol id="i-globe" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><path d="M3.8 12h16.4M12 3.8c2.3 2.2 3.4 5 3.4 8.2s-1.1 6-3.4 8.2c-2.3-2.2-3.4-5-3.4-8.2s1.1-6 3.4-8.2z"/></symbol>' +
    '<symbol id="i-key" viewBox="0 0 24 24"><circle cx="8" cy="14.5" r="4"/><path d="M11 11.5L19.5 3M16 6.5l2.5 2.5M13.8 8.7l2.2 2.2"/></symbol>' +
    '<symbol id="i-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><path d="M12 11v5M12 7.8v.4"/></symbol>' +
    '<symbol id="i-doc" viewBox="0 0 24 24"><path d="M6.5 3.5h7l4.5 4.5v12.5h-11.5z"/><path d="M9 12h6M9 15.5h6"/></symbol>' +
  '</svg>';
  var holder = document.createElement('div');
  holder.innerHTML = svg;
  if (document.body) { insert(); } else { document.addEventListener('DOMContentLoaded', insert); }
  function insert() {
    document.body.insertBefore(holder.firstChild, document.body.firstChild);
  }
})();