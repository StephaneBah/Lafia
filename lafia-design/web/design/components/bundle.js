/* @ds-bundle: {"format":4,"namespace":"Lafia","components":[{"name":"Logo"},{"name":"Icon"},{"name":"Picto"},{"name":"Button"},{"name":"TextInput"},{"name":"NpiField"},{"name":"CodeField"},{"name":"StatusBadge"},{"name":"OrdonnanceLine"},{"name":"TimelineItem"},{"name":"Alert"},{"name":"Card"},{"name":"Table"},{"name":"SiteHeader"},{"name":"SiteFooter"},{"name":"AppHeader"},{"name":"ServiceCard"},{"name":"DemoAccount"},{"name":"SoonCard"}]} */
(function () {
  var React = window.React;
  var h = React.createElement;
  var useState = React.useState, useEffect = React.useEffect, useRef = React.useRef, useId = React.useId;
  var ICONS = {"arrow-left": "<path d=\"M228,128a12,12,0,0,1-12,12H69l51.52,51.51a12,12,0,0,1-17,17l-72-72a12,12,0,0,1,0-17l72-72a12,12,0,0,1,17,17L69,116H216A12,12,0,0,1,228,128Z\"/>", "arrow-square-out": "<path d=\"M228,104a12,12,0,0,1-24,0V69l-59.51,59.51a12,12,0,0,1-17-17L187,52H152a12,12,0,0,1,0-24h64a12,12,0,0,1,12,12Zm-44,24a12,12,0,0,0-12,12v64H52V84h64a12,12,0,0,0,0-24H48A20,20,0,0,0,28,80V208a20,20,0,0,0,20,20H176a20,20,0,0,0,20-20V140A12,12,0,0,0,184,128Z\"/>", "calendar-blank": "<path d=\"M208,28H188V24a12,12,0,0,0-24,0v4H92V24a12,12,0,0,0-24,0v4H48A20,20,0,0,0,28,48V208a20,20,0,0,0,20,20H208a20,20,0,0,0,20-20V48A20,20,0,0,0,208,28ZM68,52a12,12,0,0,0,24,0h72a12,12,0,0,0,24,0h16V76H52V52ZM52,204V100H204V204Z\"/>", "caret-down": "<path d=\"M216.49,104.49l-80,80a12,12,0,0,1-17,0l-80-80a12,12,0,0,1,17-17L128,159l71.51-71.52a12,12,0,0,1,17,17Z\"/>", "cash-register": "<path d=\"M243.61,157,221.17,71a20,20,0,0,0-19.35-15H140V40a20,20,0,0,0-20-20H80A20,20,0,0,0,60,40V56H54.18A20,20,0,0,0,34.83,71L12.39,157a11.94,11.94,0,0,0-.39,3v32a20,20,0,0,0,20,20H224a20,20,0,0,0,20-20V160A11.94,11.94,0,0,0,243.61,157ZM84,44h32V56H84ZM57.27,80H198.73l17.74,68H39.53ZM36,188V172H220v16Zm28-72a12,12,0,0,1,12-12h8a12,12,0,0,1,0,24H76A12,12,0,0,1,64,116Zm48,0a12,12,0,0,1,12-12h8a12,12,0,0,1,0,24h-8A12,12,0,0,1,112,116Zm48,0a12,12,0,0,1,12-12h8a12,12,0,0,1,0,24h-8A12,12,0,0,1,160,116Z\"/>", "chart-line": "<path d=\"M236,208a12,12,0,0,1-12,12H32a12,12,0,0,1-12-12V48a12,12,0,0,1,24,0v85.55L88.1,95a12,12,0,0,1,15.1-.57l56.22,42.16L216.1,87A12,12,0,1,1,231.9,105l-64,56a12,12,0,0,1-15.1.57L96.58,119.44,44,165.45V196H224A12,12,0,0,1,236,208Z\"/>", "check": "<path d=\"M232.49,80.49l-128,128a12,12,0,0,1-17,0l-56-56a12,12,0,1,1,17-17L96,183,215.51,63.51a12,12,0,0,1,17,17Z\"/>", "clock": "<path d=\"M128,20A108,108,0,1,0,236,128,108.12,108.12,0,0,0,128,20Zm0,192a84,84,0,1,1,84-84A84.09,84.09,0,0,1,128,212Zm68-84a12,12,0,0,1-12,12H128a12,12,0,0,1-12-12V72a12,12,0,0,1,24,0v44h44A12,12,0,0,1,196,128Z\"/>", "copy": "<path d=\"M216,28H88A12,12,0,0,0,76,40V76H40A12,12,0,0,0,28,88V216a12,12,0,0,0,12,12H168a12,12,0,0,0,12-12V180h36a12,12,0,0,0,12-12V40A12,12,0,0,0,216,28ZM156,204H52V100H156Zm48-48H180V88a12,12,0,0,0-12-12H100V52H204Z\"/>", "eye": "<path d=\"M251,123.13c-.37-.81-9.13-20.26-28.48-39.61C196.63,57.67,164,44,128,44S59.37,57.67,33.51,83.52C14.16,102.87,5.4,122.32,5,123.13a12.08,12.08,0,0,0,0,9.75c.37.82,9.13,20.26,28.49,39.61C59.37,198.34,92,212,128,212s68.63-13.66,94.48-39.51c19.36-19.35,28.12-38.79,28.49-39.61A12.08,12.08,0,0,0,251,123.13Zm-46.06,33C183.47,177.27,157.59,188,128,188s-55.47-10.73-76.91-31.88A130.36,130.36,0,0,1,29.52,128,130.45,130.45,0,0,1,51.09,99.89C72.54,78.73,98.41,68,128,68s55.46,10.73,76.91,31.89A130.36,130.36,0,0,1,226.48,128,130.45,130.45,0,0,1,204.91,156.12ZM128,84a44,44,0,1,0,44,44A44.05,44.05,0,0,0,128,84Zm0,64a20,20,0,1,1,20-20A20,20,0,0,1,128,148Z\"/>", "flask": "<path d=\"M225.15,197.71,164,95.81V44h4a12,12,0,0,0,0-24H88a12,12,0,0,0,0,24h4V95.81L30.85,197.71A20,20,0,0,0,48,228H208a20,20,0,0,0,17.15-30.29ZM140,44V99.14a12,12,0,0,0,1.71,6.17l35.13,58.54c-10.79.86-25.15-1.31-43.42-10.56-14-7.08-27.46-11.33-40.27-12.76l21.14-35.22A12,12,0,0,0,116,99.14V44ZM55.06,204,79,164.19c13-1.11,27.62,2.42,43.62,10.52,19.61,9.92,36.25,13.31,49.85,13.31A75.44,75.44,0,0,0,190.11,186l10.83,18Z\"/>", "github-logo": "<path d=\"M212.62,75.17A63.7,63.7,0,0,0,206.39,26,12,12,0,0,0,196,20a63.71,63.71,0,0,0-50,24H126A63.71,63.71,0,0,0,76,20a12,12,0,0,0-10.39,6,63.7,63.7,0,0,0-6.23,49.17A61.5,61.5,0,0,0,52,104v8a60.1,60.1,0,0,0,45.76,58.28A43.66,43.66,0,0,0,92,192v4H76a20,20,0,0,1-20-20,44.05,44.05,0,0,0-44-44,12,12,0,0,0,0,24,20,20,0,0,1,20,20,44.05,44.05,0,0,0,44,44H92v12a12,12,0,0,0,24,0V192a20,20,0,0,1,40,0v40a12,12,0,0,0,24,0V192a43.66,43.66,0,0,0-5.76-21.72A60.1,60.1,0,0,0,220,112v-8A61.5,61.5,0,0,0,212.62,75.17ZM196,112a36,36,0,0,1-36,36H112a36,36,0,0,1-36-36v-8a37.87,37.87,0,0,1,6.13-20.12,11.65,11.65,0,0,0,1.58-11.49,39.9,39.9,0,0,1-.4-27.72,39.87,39.87,0,0,1,26.41,17.8A12,12,0,0,0,119.82,68h32.35a12,12,0,0,0,10.11-5.53,39.84,39.84,0,0,1,26.41-17.8,39.9,39.9,0,0,1-.4,27.72,12,12,0,0,0,1.61,11.53A37.85,37.85,0,0,1,196,104Z\"/>", "heartbeat": "<path d=\"M71.76,148H31.7a12,12,0,1,1,0-24H65.33l12.45-18.66a12,12,0,0,1,20,0l22,33,6-9a12,12,0,0,1,10-5.34h24a12,12,0,1,1,0,24h-17.6l-12.46,18.66a12,12,0,0,1-20,0l-22-33-6,9A12,12,0,0,1,71.76,148ZM177.91,36c-20.12,0-38,7.93-50.07,21.56C115.74,43.93,97.89,36,77.76,36A66,66,0,0,0,12.07,94.68,12,12,0,0,0,36,97.32,42,42,0,0,1,77.76,60c17.83,0,32.75,9.4,38.95,24.54a12,12,0,0,0,22.25,0C145.16,69.4,160.08,60,177.91,60A42.08,42.08,0,0,1,220,102c0,29.42-25.86,57.77-47.56,76.36a329,329,0,0,1-44.58,31.81c-10.87-6.45-35.37-22-56.51-42.73a12,12,0,1,0-16.84,17.12c30.39,29.81,66.15,49.2,67.66,50a12.06,12.06,0,0,0,11.39,0C138,232.14,244,174.34,244,102A66.12,66.12,0,0,0,177.91,36Z\"/>", "hospital": "<path d=\"M244,204h-4V128a20,20,0,0,0-20-20H172V48a20,20,0,0,0-20-20H56A20,20,0,0,0,36,48V204H32a12,12,0,0,0,0,24H244a12,12,0,0,0,0-24Zm-28-72v72H172V132ZM60,52h88V204H136V160a12,12,0,0,0-12-12H84a12,12,0,0,0-12,12v44H60Zm52,152H96V172h16ZM72,96A12,12,0,0,1,84,84h8V76a12,12,0,0,1,24,0v8h8a12,12,0,0,1,0,24h-8v8a12,12,0,0,1-24,0v-8H84A12,12,0,0,1,72,96Z\"/>", "house": "<path d=\"M222.14,105.85l-80-80a20,20,0,0,0-28.28,0l-80,80A19.86,19.86,0,0,0,28,120v96a12,12,0,0,0,12,12h64a12,12,0,0,0,12-12V164h24v52a12,12,0,0,0,12,12h64a12,12,0,0,0,12-12V120A19.86,19.86,0,0,0,222.14,105.85ZM204,204H164V152a12,12,0,0,0-12-12H104a12,12,0,0,0-12,12v52H52V121.65l76-76,76,76Z\"/>", "identification-card": "<path d=\"M148,108a12,12,0,0,1,12-12h28a12,12,0,0,1,0,24H160A12,12,0,0,1,148,108Zm40,28H168a12,12,0,0,0,0,24h20a12,12,0,0,0,0-24Zm48-80V200a20,20,0,0,1-20,20H40a20,20,0,0,1-20-20V56A20,20,0,0,1,40,36H216A20,20,0,0,1,236,56Zm-24,4H44V196H212ZM58.28,159.37A43.82,43.82,0,0,1,71.53,142a36,36,0,1,1,56.94,0,43.84,43.84,0,0,1,13.26,17.37,12,12,0,0,1-22.15,9.26C116.48,161.19,108.42,156,100,156s-16.47,5.2-19.59,12.63a12,12,0,1,1-22.13-9.26ZM88,120a12,12,0,1,0,12-12A12,12,0,0,0,88,120Z\"/>", "info": "<path d=\"M108,84a16,16,0,1,1,16,16A16,16,0,0,1,108,84Zm128,44A108,108,0,1,1,128,20,108.12,108.12,0,0,1,236,128Zm-24,0a84,84,0,1,0-84,84A84.09,84.09,0,0,0,212,128Zm-72,36.68V132a20,20,0,0,0-20-20,12,12,0,0,0-4,23.32V168a20,20,0,0,0,20,20,12,12,0,0,0,4-23.32Z\"/>", "list": "<path d=\"M228,128a12,12,0,0,1-12,12H40a12,12,0,0,1,0-24H216A12,12,0,0,1,228,128ZM40,76H216a12,12,0,0,0,0-24H40a12,12,0,0,0,0,24ZM216,180H40a12,12,0,0,0,0,24H216a12,12,0,0,0,0-24Z\"/>", "lock-simple": "<path d=\"M208,76H180V56A52,52,0,0,0,76,56V76H48A20,20,0,0,0,28,96V208a20,20,0,0,0,20,20H208a20,20,0,0,0,20-20V96A20,20,0,0,0,208,76ZM100,56a28,28,0,0,1,56,0V76H100ZM204,204H52V100H204Z\"/>", "magnifying-glass": "<path d=\"M232.49,215.51,185,168a92.12,92.12,0,1,0-17,17l47.53,47.54a12,12,0,0,0,17-17ZM44,112a68,68,0,1,1,68,68A68.07,68.07,0,0,1,44,112Z\"/>", "microphone": "<path d=\"M128,180a52.06,52.06,0,0,0,52-52V64A52,52,0,0,0,76,64v64A52.06,52.06,0,0,0,128,180ZM100,64a28,28,0,0,1,56,0v64a28,28,0,0,1-56,0Zm40,155.22V240a12,12,0,0,1-24,0V219.22A92.14,92.14,0,0,1,36,128a12,12,0,0,1,24,0,68,68,0,0,0,136,0,12,12,0,0,1,24,0A92.14,92.14,0,0,1,140,219.22Z\"/>", "money": "<path d=\"M240,52H16A12,12,0,0,0,4,64V192a12,12,0,0,0,12,12H240a12,12,0,0,0,12-12V64A12,12,0,0,0,240,52ZM181.21,180H74.79A60.18,60.18,0,0,0,28,133.21V122.79A60.18,60.18,0,0,0,74.79,76H181.21A60.18,60.18,0,0,0,228,122.79v10.42A60.18,60.18,0,0,0,181.21,180ZM228,97.94A36.23,36.23,0,0,1,206.06,76H228ZM49.94,76A36.23,36.23,0,0,1,28,97.94V76ZM28,158.06A36.23,36.23,0,0,1,49.94,180H28ZM206.06,180A36.23,36.23,0,0,1,228,158.06V180ZM128,88a40,40,0,1,0,40,40A40,40,0,0,0,128,88Zm0,56a16,16,0,1,1,16-16A16,16,0,0,1,128,144Z\"/>", "moon": "<path d=\"M236.37,139.4a12,12,0,0,0-12-3A84.07,84.07,0,0,1,119.6,31.59a12,12,0,0,0-15-15A108.86,108.86,0,0,0,49.69,55.07,108,108,0,0,0,136,228a107.09,107.09,0,0,0,64.93-21.69,108.86,108.86,0,0,0,38.44-54.94A12,12,0,0,0,236.37,139.4Zm-49.88,47.74A84,84,0,0,1,68.86,69.51,84.93,84.93,0,0,1,92.27,48.29Q92,52.13,92,56A108.12,108.12,0,0,0,200,164q3.87,0,7.71-.27A84.79,84.79,0,0,1,186.49,187.14Z\"/>", "pill": "<path d=\"M219.26,36.77a57.28,57.28,0,0,0-81,0L36.77,138.26a57.26,57.26,0,0,0,81,81L219.26,117.74A57.33,57.33,0,0,0,219.26,36.77ZM100.78,202.26a33.26,33.26,0,1,1-47-47L96,113l47,47Zm101.5-101.49L160,143,113,96l42.27-42.26a33.26,33.26,0,0,1,47,47Zm-9.77-25.26a12,12,0,0,1,0,17l-24,24a12,12,0,1,1-17-17l24-24A12,12,0,0,1,192.51,75.51Z\"/>", "plus": "<path d=\"M228,128a12,12,0,0,1-12,12H140v76a12,12,0,0,1-24,0V140H40a12,12,0,0,1,0-24h76V40a12,12,0,0,1,24,0v76h76A12,12,0,0,1,228,128Z\"/>", "printer": "<path d=\"M214.67,68H204V40a12,12,0,0,0-12-12H64A12,12,0,0,0,52,40V68H41.33C25.16,68,12,80.56,12,96v80a12,12,0,0,0,12,12H52v28a12,12,0,0,0,12,12H192a12,12,0,0,0,12-12V188h28a12,12,0,0,0,12-12V96C244,80.56,230.84,68,214.67,68ZM76,52H180V68H76ZM180,204H76V172H180Zm40-40H204v-4a12,12,0,0,0-12-12H64a12,12,0,0,0-12,12v4H36V96c0-2.17,2.44-4,5.33-4H214.67c2.89,0,5.33,1.83,5.33,4Zm-16-44a16,16,0,1,1-16-16A16,16,0,0,1,204,120Z\"/>", "qr-code": "<path d=\"M100,36H56A20,20,0,0,0,36,56v44a20,20,0,0,0,20,20h44a20,20,0,0,0,20-20V56A20,20,0,0,0,100,36ZM96,96H60V60H96Zm4,40H56a20,20,0,0,0-20,20v44a20,20,0,0,0,20,20h44a20,20,0,0,0,20-20V156A20,20,0,0,0,100,136Zm-4,60H60V160H96ZM200,36H156a20,20,0,0,0-20,20v44a20,20,0,0,0,20,20h44a20,20,0,0,0,20-20V56A20,20,0,0,0,200,36Zm-4,60H160V60h36Zm-60,76V148a12,12,0,0,1,24,0v24a12,12,0,0,1-24,0Zm84-8a12,12,0,0,1-12,12H196v32a12,12,0,0,1-12,12H148a12,12,0,0,1,0-24h24V148a12,12,0,0,1,24,0v4h12A12,12,0,0,1,220,164Z\"/>", "receipt": "<path d=\"M68,100A12,12,0,0,1,80,88h96a12,12,0,0,1,0,24H80A12,12,0,0,1,68,100Zm12,52h96a12,12,0,0,0,0-24H80a12,12,0,0,0,0,24ZM236,56V208a12,12,0,0,1-17.37,10.73L192,205.42l-26.63,13.31a12,12,0,0,1-10.74,0L128,205.42l-26.63,13.31a12,12,0,0,1-10.74,0L64,205.42,37.37,218.73A12,12,0,0,1,20,208V56A20,20,0,0,1,40,36H216A20,20,0,0,1,236,56Zm-24,4H44V188.58l14.63-7.31a12,12,0,0,1,10.74,0L96,194.58l26.63-13.31a12,12,0,0,1,10.74,0L160,194.58l26.63-13.31a12,12,0,0,1,10.74,0L212,188.58Z\"/>", "shield-check": "<path d=\"M208,36H48A20,20,0,0,0,28,56v56c0,54.29,26.32,87.22,48.4,105.29,23.71,19.39,47.44,26,48.44,26.29a12.1,12.1,0,0,0,6.32,0c1-.28,24.73-6.9,48.44-26.29,22.08-18.07,48.4-51,48.4-105.29V56A20,20,0,0,0,208,36Zm-4,76c0,35.71-13.09,64.69-38.91,86.15A126.28,126.28,0,0,1,128,219.38a126.14,126.14,0,0,1-37.09-21.23C65.09,176.69,52,147.71,52,112V60H204ZM79.51,144.49a12,12,0,1,1,17-17L112,143l47.51-47.52a12,12,0,0,1,17,17l-56,56a12,12,0,0,1-17,0Z\"/>", "sign-out": "<path d=\"M124,216a12,12,0,0,1-12,12H48a12,12,0,0,1-12-12V40A12,12,0,0,1,48,28h64a12,12,0,0,1,0,24H60V204h52A12,12,0,0,1,124,216Zm108.49-96.49-40-40a12,12,0,0,0-17,17L195,116H112a12,12,0,0,0,0,24h83l-19.52,19.51a12,12,0,0,0,17,17l40-40A12,12,0,0,0,232.49,119.51Z\"/>", "stethoscope": "<path d=\"M248,160a40,40,0,1,0-52.64,37.94A28,28,0,0,1,168,220H144a28,28,0,0,1-28-28V154.9c31.73-5.78,56-34.09,56-67.73V40a12,12,0,0,0-12-12H136a12,12,0,0,0,0,24h12V87.17c0,24.4-19.47,44.52-43.41,44.83A44,44,0,0,1,60,88V52H72a12,12,0,0,0,0-24H48A12,12,0,0,0,36,40V88a68,68,0,0,0,56,66.93V192a52.06,52.06,0,0,0,52,52h24a52.06,52.06,0,0,0,51.61-45.72A40.08,40.08,0,0,0,248,160Zm-40,16a16,16,0,1,1,16-16A16,16,0,0,1,208,176Z\"/>", "sun": "<path d=\"M116,36V20a12,12,0,0,1,24,0V36a12,12,0,0,1-24,0Zm80,92a68,68,0,1,1-68-68A68.07,68.07,0,0,1,196,128Zm-24,0a44,44,0,1,0-44,44A44.05,44.05,0,0,0,172,128ZM51.51,68.49a12,12,0,1,0,17-17l-12-12a12,12,0,0,0-17,17Zm0,119-12,12a12,12,0,0,0,17,17l12-12a12,12,0,1,0-17-17ZM196,72a12,12,0,0,0,8.49-3.51l12-12a12,12,0,0,0-17-17l-12,12A12,12,0,0,0,196,72Zm8.49,115.51a12,12,0,0,0-17,17l12,12a12,12,0,0,0,17-17ZM48,128a12,12,0,0,0-12-12H20a12,12,0,0,0,0,24H36A12,12,0,0,0,48,128Zm80,80a12,12,0,0,0-12,12v16a12,12,0,0,0,24,0V220A12,12,0,0,0,128,208Zm108-92H220a12,12,0,0,0,0,24h16a12,12,0,0,0,0-24Z\"/>", "test-tube": "<path d=\"M240.49,83.51l-60-60a12,12,0,0,0-17,0L34.28,152.75a48.77,48.77,0,0,0,69,69L214.48,110.49l21.31-7.11a12,12,0,0,0,4.7-19.87ZM86.28,204.75a24.77,24.77,0,0,1-35-35l28.13-28.13c7.73-2.41,19.58-3,35.06,5a83.94,83.94,0,0,0,21.95,8ZM204.2,88.62a12.15,12.15,0,0,0-4.69,2.89l-38.89,38.9c-7.73,2.41-19.58,3-35.06-5a83.94,83.94,0,0,0-21.94-8L172,49l37.79,37.79Z\"/>", "user": "<path d=\"M234.38,210a123.36,123.36,0,0,0-60.78-53.23,76,76,0,1,0-91.2,0A123.36,123.36,0,0,0,21.62,210a12,12,0,1,0,20.77,12c18.12-31.32,50.12-50,85.61-50s67.49,18.69,85.61,50a12,12,0,0,0,20.77-12ZM76,96a52,52,0,1,1,52,52A52.06,52.06,0,0,1,76,96Z\"/>", "users": "<path d=\"M125.18,156.94a64,64,0,1,0-82.36,0,100.23,100.23,0,0,0-39.49,32,12,12,0,0,0,19.35,14.2,76,76,0,0,1,122.64,0,12,12,0,0,0,19.36-14.2A100.33,100.33,0,0,0,125.18,156.94ZM44,108a40,40,0,1,1,40,40A40,40,0,0,1,44,108Zm206.1,97.67a12,12,0,0,1-16.78-2.57A76.31,76.31,0,0,0,172,172a12,12,0,0,1,0-24,40,40,0,1,0-10.3-78.67,12,12,0,1,1-6.16-23.19,64,64,0,0,1,57.64,110.8,100.23,100.23,0,0,1,39.49,32A12,12,0,0,1,250.1,205.67Z\"/>", "video-camera": "<path d=\"M249.45,69.31a12,12,0,0,0-12.51,1L212,88.43V72a20,20,0,0,0-20-20H32A20,20,0,0,0,12,72V184a20,20,0,0,0,20,20H192a20,20,0,0,0,20-20V167.57l24.94,18.14A12,12,0,0,0,256,176V80A12,12,0,0,0,249.45,69.31ZM188,180H36V76H188Zm44-27.57-20-14.54V118.11l20-14.54Z\"/>", "warning": "<path d=\"M240.26,186.1,152.81,34.23h0a28.74,28.74,0,0,0-49.62,0L15.74,186.1a27.45,27.45,0,0,0,0,27.71A28.31,28.31,0,0,0,40.55,228h174.9a28.31,28.31,0,0,0,24.79-14.19A27.45,27.45,0,0,0,240.26,186.1Zm-20.8,15.7a4.46,4.46,0,0,1-4,2.2H40.55a4.46,4.46,0,0,1-4-2.2,3.56,3.56,0,0,1,0-3.73L124,46.2a4.77,4.77,0,0,1,8,0l87.44,151.87A3.56,3.56,0,0,1,219.46,201.8ZM116,136V104a12,12,0,0,1,24,0v32a12,12,0,0,1-24,0Zm28,40a16,16,0,1,1-16-16A16,16,0,0,1,144,176Z\"/>", "warning-octagon": "<path d=\"M116,132V80a12,12,0,0,1,24,0v52a12,12,0,0,1-24,0ZM236,91.55v72.9a19.86,19.86,0,0,1-5.86,14.14l-51.55,51.55A19.85,19.85,0,0,1,164.45,236H91.55a19.85,19.85,0,0,1-14.14-5.86L25.86,178.59A19.86,19.86,0,0,1,20,164.45V91.55a19.86,19.86,0,0,1,5.86-14.14L77.41,25.86A19.85,19.85,0,0,1,91.55,20h72.9a19.85,19.85,0,0,1,14.14,5.86l51.55,51.55A19.86,19.86,0,0,1,236,91.55Zm-24,1.66L162.79,44H93.21L44,93.21v69.58L93.21,212h69.58L212,162.79ZM128,156a16,16,0,1,0,16,16A16,16,0,0,0,128,156Z\"/>", "x": "<path d=\"M208.49,191.51a12,12,0,0,1-17,17L128,145,64.49,208.49a12,12,0,0,1-17-17L111,128,47.51,64.49a12,12,0,0,1,17-17L128,111l63.51-63.52a12,12,0,0,1,17,17L145,128Z\"/>", "d:hospital": "<path d=\"M160,48V216H128V160H80v56H48V48a8,8,0,0,1,8-8h96A8,8,0,0,1,160,48Z\" opacity=\"0.2\"/><path d=\"M248,208h-8V128a16,16,0,0,0-16-16H168V48a16,16,0,0,0-16-16H56A16,16,0,0,0,40,48V208H32a8,8,0,0,0,0,16H248a8,8,0,0,0,0-16Zm-24-80v80H168V128ZM56,48h96V208H136V160a8,8,0,0,0-8-8H80a8,8,0,0,0-8,8v48H56Zm64,160H88V168h32ZM72,96a8,8,0,0,1,8-8H96V72a8,8,0,0,1,16,0V88h16a8,8,0,0,1,0,16H112v16a8,8,0,0,1-16,0V104H80A8,8,0,0,1,72,96Z\"/>", "d:stethoscope": "<path d=\"M240,160a32,32,0,1,1-32-32A32,32,0,0,1,240,160Z\" opacity=\"0.2\"/><path d=\"M220,160a12,12,0,1,1-12-12A12,12,0,0,1,220,160Zm-4.55,39.29A48.08,48.08,0,0,1,168,240H144a48.05,48.05,0,0,1-48-48V151.49A64,64,0,0,1,40,88V40a8,8,0,0,1,8-8H72a8,8,0,0,1,0,16H56V88a48,48,0,0,0,48.64,48c26.11-.34,47.36-22.25,47.36-48.83V48H136a8,8,0,0,1,0-16h24a8,8,0,0,1,8,8V87.17c0,32.84-24.53,60.29-56,64.31V192a32,32,0,0,0,32,32h24a32.06,32.06,0,0,0,31.22-25,40,40,0,1,1,16.23.27ZM232,160a24,24,0,1,0-24,24A24,24,0,0,0,232,160Z\"/>", "d:test-tube": "<path d=\"M167.18,140.82,94.77,213.23a36.77,36.77,0,0,1-52,0h0a36.77,36.77,0,0,1,0-52l30-30c9.37-3.65,25.78-6.36,47.18,4.82S157.81,144.47,167.18,140.82Z\" opacity=\"0.2\"/><path d=\"M237.66,86.34l-60-60a8,8,0,0,0-11.32,0L37.11,155.57a44.77,44.77,0,0,0,63.32,63.32L212.32,107l22.21-7.4a8,8,0,0,0,3.13-13.25ZM89.11,207.57a28.77,28.77,0,0,1-40.68-40.68l28.8-28.8c8.47-2.9,21.75-4,39.07,5,10.6,5.54,20.18,8,28.56,8.73ZM205.47,92.41a8,8,0,0,0-3.13,1.93l-39.57,39.57c-8.47,2.9-21.75,4-39.07-5-10.6-5.54-20.18-8-28.56-8.73L172,43.31,217.19,88.5Z\"/>", "d:user": "<path d=\"M192,96a64,64,0,1,1-64-64A64,64,0,0,1,192,96Z\" opacity=\"0.2\"/><path d=\"M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z\"/>", "d:receipt": "<path d=\"M224,56V208l-32-16-32,16-32-16L96,208,64,192,32,208V56a8,8,0,0,1,8-8H216A8,8,0,0,1,224,56Z\" opacity=\"0.2\"/><path d=\"M72,104a8,8,0,0,1,8-8h96a8,8,0,0,1,0,16H80A8,8,0,0,1,72,104Zm8,40h96a8,8,0,0,0,0-16H80a8,8,0,0,0,0,16ZM232,56V208a8,8,0,0,1-11.58,7.15L192,200.94l-28.42,14.21a8,8,0,0,1-7.16,0L128,200.94,99.58,215.15a8,8,0,0,1-7.16,0L64,200.94,35.58,215.15A8,8,0,0,1,24,208V56A16,16,0,0,1,40,40H216A16,16,0,0,1,232,56Zm-16,0H40V195.06l20.42-10.22a8,8,0,0,1,7.16,0L96,199.06l28.42-14.22a8,8,0,0,1,7.16,0L160,199.06l28.42-14.22a8,8,0,0,1,7.16,0L216,195.06Z\"/>", "d:microphone": "<path d=\"M168,64v64a40,40,0,0,1-40,40h0a40,40,0,0,1-40-40V64a40,40,0,0,1,40-40h0A40,40,0,0,1,168,64Z\" opacity=\"0.2\"/><path d=\"M128,176a48.05,48.05,0,0,0,48-48V64a48,48,0,0,0-96,0v64A48.05,48.05,0,0,0,128,176ZM96,64a32,32,0,0,1,64,0v64a32,32,0,0,1-64,0Zm40,143.6V240a8,8,0,0,1-16,0V207.6A80.11,80.11,0,0,1,48,128a8,8,0,0,1,16,0,64,64,0,0,0,128,0,8,8,0,0,1,16,0A80.11,80.11,0,0,1,136,207.6Z\"/>", "d:pill": "<path d=\"M160,160l-50.75,50.75a45.26,45.26,0,0,1-64,0h0a45.26,45.26,0,0,1,0-64L96,96Z\" opacity=\"0.2\"/><path d=\"M216.43,39.6a53.27,53.27,0,0,0-75.33,0L39.6,141.09a53.26,53.26,0,0,0,75.32,75.31L216.43,114.91A53.32,53.32,0,0,0,216.43,39.6ZM103.61,205.09h0a37.26,37.26,0,0,1-52.7-52.69L96,107.31,148.7,160ZM205.11,103.6,160,148.69,107.32,96l45.1-45.09a37.26,37.26,0,0,1,52.69,52.69ZM189.68,82.34a8,8,0,0,1,0,11.32l-24,24a8,8,0,1,1-11.31-11.32l24-24A8,8,0,0,1,189.68,82.34Z\"/>", "d:cash-register": "<path d=\"M232,160H24L46.49,70.06A8,8,0,0,1,54.25,64h147.5a8,8,0,0,1,7.76,6.06Z\" opacity=\"0.2\"/><path d=\"M239.76,158.06,217.28,68.12A16,16,0,0,0,201.75,56H136V40a16,16,0,0,0-16-16H80A16,16,0,0,0,64,40V56H54.25A16,16,0,0,0,38.72,68.12L16.24,158.06A7.93,7.93,0,0,0,16,160v32a16,16,0,0,0,16,16H224a16,16,0,0,0,16-16V160A7.93,7.93,0,0,0,239.76,158.06ZM80,40h40V56H80ZM54.25,72h147.5l20,80H34.25ZM32,192V168H224v24ZM64,96a8,8,0,0,1,8-8H88a8,8,0,0,1,0,16H72A8,8,0,0,1,64,96Zm48,0a8,8,0,0,1,8-8h16a8,8,0,0,1,0,16H120A8,8,0,0,1,112,96Zm48,0a8,8,0,0,1,8-8h16a8,8,0,0,1,0,16H168A8,8,0,0,1,160,96ZM64,128a8,8,0,0,1,8-8H88a8,8,0,0,1,0,16H72A8,8,0,0,1,64,128Zm48,0a8,8,0,0,1,8-8h16a8,8,0,0,1,0,16H120A8,8,0,0,1,112,128Zm48,0a8,8,0,0,1,8-8h16a8,8,0,0,1,0,16H168A8,8,0,0,1,160,128Z\"/>", "d:chart-line": "<path d=\"M224,64V208H32V48H208A16,16,0,0,1,224,64Z\" opacity=\"0.2\"/><path d=\"M232,208a8,8,0,0,1-8,8H32a8,8,0,0,1-8-8V48a8,8,0,0,1,16,0v94.37L90.73,98a8,8,0,0,1,10.07-.38l58.81,44.11L218.73,90a8,8,0,1,1,10.54,12l-64,56a8,8,0,0,1-10.07.38L96.39,114.29,40,163.63V200H224A8,8,0,0,1,232,208Z\"/>", "d:video-camera": "<path d=\"M200,72V184a8,8,0,0,1-8,8H32a8,8,0,0,1-8-8V72a8,8,0,0,1,8-8H192A8,8,0,0,1,200,72Z\" opacity=\"0.2\"/><path d=\"M251.77,73a8,8,0,0,0-8.21.39L208,97.05V72a16,16,0,0,0-16-16H32A16,16,0,0,0,16,72V184a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V159l35.56,23.71A8,8,0,0,0,248,184a8,8,0,0,0,8-8V80A8,8,0,0,0,251.77,73ZM192,184H32V72H192V184Zm48-22.95-32-21.33V116.28L240,95Z\"/>"};
  var PICTOS = {"retire": "<path d=\"M8 18 H34 V42 H8 Z\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M8 18 l4 -8 H30 l4 8\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><circle cx=\"35\" cy=\"34\" r=\"9\" fill=\"#121212\"/><path d=\"M31 34 l3 3 5 -5\" fill=\"none\" stroke=\"#FFFFFF\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "paye": "<path d=\"M10 5 H34 V41 l-4 -3 -4 3 -4 -3 -4 3 -4 -3 -4 3 Z\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M15 13 H29 M15 19 H25\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><circle cx=\"33\" cy=\"31\" r=\"10\" fill=\"#00524B\" stroke=\"#121212\" stroke-width=\"3\"/><path d=\"M28.5 31 l3 3 6 -6\" fill=\"none\" stroke=\"#FFFFFF\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "soir": "<rect x=\"3\" y=\"6\" width=\"42\" height=\"28\" rx=\"6\" fill=\"#C0C6FC\"/><path d=\"M14 34 A10 10 0 0 1 34 34 Z\" fill=\"#F2B544\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M4 34 H44\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M24 37 V43 M20 40 l4 4 4 -4\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "nuit": "<circle cx=\"24\" cy=\"24\" r=\"21\" fill=\"#242A36\"/><path d=\"M29 11 A14 14 0 1 0 36 31 A11 11 0 0 1 29 11 Z\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M34 13 v6 M31 16 h6\" stroke=\"#FFFFFF\" stroke-width=\"2.5\" stroke-linecap=\"round\"/>", "a-retirer": "<path d=\"M6 18 H30 V42 H6 Z\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M6 18 l4 -8 H26 l4 8\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M12 28 H24\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M33 30 H45 M40 25 l5 5 -5 5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "comprime": "<path d=\"M8 22 v6 a16 8 0 0 0 32 0 v-6\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><ellipse cx=\"24\" cy=\"22\" rx=\"16\" ry=\"8\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M16 22 H32\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "a-payer": "<rect x=\"4\" y=\"12\" width=\"30\" height=\"20\" rx=\"4\" fill=\"#DCF2EE\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><circle cx=\"19\" cy=\"22\" r=\"5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><ellipse cx=\"36\" cy=\"37\" rx=\"9\" ry=\"4\" fill=\"#F2B544\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M27 31 v6 M45 31 v6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><ellipse cx=\"36\" cy=\"31\" rx=\"9\" ry=\"4\" fill=\"#F2B544\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/>", "consultation": "<path d=\"M4 12 a3 3 0 0 1 3 -3 H18 l4 5 H41 a3 3 0 0 1 3 3 V38 a3 3 0 0 1 -3 3 H7 a3 3 0 0 1 -3 -3 Z\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M11 28 q13 -12 26 0 q-13 12 -26 0 Z\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><circle cx=\"24\" cy=\"28\" r=\"4\" fill=\"#121212\"/>", "urgence": "<path d=\"M14 36 V26 a10 10 0 0 1 20 0 V36 Z\" fill=\"#9A1C15\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\"/><path d=\"M20 26 a4 4 0 0 1 4 -4\" stroke=\"#FFFFFF\" stroke-width=\"3\" fill=\"none\" stroke-linecap=\"round\"/><rect x=\"9\" y=\"36\" width=\"30\" height=\"7\" rx=\"2\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><line x1=\"38.1\" y1=\"20.9\" x2=\"42.8\" y2=\"19.2\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"32.6\" y1=\"13.7\" x2=\"35.5\" y2=\"9.6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"24.0\" y1=\"11.0\" x2=\"24.0\" y2=\"6.0\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"15.4\" y1=\"13.7\" x2=\"12.5\" y2=\"9.6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"9.9\" y1=\"20.9\" x2=\"5.2\" y2=\"19.2\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "jours": "<rect x=\"7\" y=\"10\" width=\"34\" height=\"31\" rx=\"5\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M7 19 H41\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><rect x=\"7\" y=\"10\" width=\"34\" height=\"9\" rx=\"4\" fill=\"#3648C0\"/><path d=\"M7 19 H41\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><rect x=\"7\" y=\"10\" width=\"34\" height=\"31\" rx=\"5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M16 6 v7 M32 6 v7\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><circle cx=\"15\" cy=\"27\" r=\"2\" fill=\"#121212\"/><circle cx=\"24\" cy=\"27\" r=\"2\" fill=\"#121212\"/><circle cx=\"33\" cy=\"27\" r=\"2\" fill=\"#121212\"/><circle cx=\"15\" cy=\"34\" r=\"2\" fill=\"#121212\"/><circle cx=\"24\" cy=\"34\" r=\"2\" fill=\"#121212\"/><circle cx=\"33\" cy=\"34\" r=\"2\" fill=\"#121212\"/>", "comprime-demi": "<path d=\"M24 30 H8 V28 v-6 A16 8 0 0 1 24 14 Z\" fill=\"#C0C6FC\" stroke=\"none\"/><path d=\"M8 22 v6 a16 8 0 0 0 16 8 V30\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M24 14 A16 8 0 0 0 8 22 A16 8 0 0 0 24 30 Z\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M28 14.5 A16 8 0 0 1 40 22 A16 8 0 0 1 28 29.5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"2\" stroke-dasharray=\"3 4\" stroke-linecap=\"round\"/>", "apres-repas": "<path d=\"M1 26 H23 A11 11 0 0 1 1 26 Z\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M7 20 q2 -3 0 -6 M14 20 q2 -3 0 -6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M22 24 H28 M25 21 l3 3 -3 3\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><g transform=\"translate(38 24) rotate(-30)\"><rect x=\"-10\" y=\"-5\" width=\"20\" height=\"10\" rx=\"5\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M0 -5 V5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><\/g>", "midi": "<circle cx=\"24\" cy=\"24\" r=\"9\" fill=\"#F2B544\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><line x1=\"38.0\" y1=\"24.0\" x2=\"43.0\" y2=\"24.0\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"33.9\" y1=\"14.1\" x2=\"37.4\" y2=\"10.6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"24.0\" y1=\"10.0\" x2=\"24.0\" y2=\"5.0\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"14.1\" y1=\"14.1\" x2=\"10.6\" y2=\"10.6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"10.0\" y1=\"24.0\" x2=\"5.0\" y2=\"24.0\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"14.1\" y1=\"33.9\" x2=\"10.6\" y2=\"37.4\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"24.0\" y1=\"38.0\" x2=\"24.0\" y2=\"43.0\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"33.9\" y1=\"33.9\" x2=\"37.4\" y2=\"37.4\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "allergie": "<g transform=\"translate(24 24) rotate(-35)\"><rect x=\"-10\" y=\"-5\" width=\"20\" height=\"10\" rx=\"5\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M0 -5 V5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><\/g><circle cx=\"24\" cy=\"24\" r=\"19\" fill=\"none\" stroke=\"#9A1C15\" stroke-width=\"5\"/><path d=\"M11 37 L37 11\" stroke=\"#9A1C15\" stroke-width=\"5\" stroke-linecap=\"round\"/>", "retire-partie": "<path d=\"M10 18 H38 V42 H10 Z\" fill=\"#FFFFFF\"/><path d=\"M10 30 H38 V42 H10 Z\" fill=\"#C0C6FC\"/><path d=\"M10 18 H38 V42 H10 Z\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M10 18 l4 -8 H34 l4 8\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M10 30 H38\" stroke=\"#121212\" stroke-width=\"2\" stroke-dasharray=\"3 4\" stroke-linecap=\"round\"/>", "avant-repas": "<g transform=\"translate(11 24) rotate(-30)\"><rect x=\"-10\" y=\"-5\" width=\"20\" height=\"10\" rx=\"5\" fill=\"#FFFFFF\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M0 -5 V5\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><\/g><path d=\"M20 24 H26 M23 21 l3 3 -3 3\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M25 26 H47 A11 11 0 0 1 25 26 Z\" fill=\"#C0C6FC\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><path d=\"M31 20 q2 -3 0 -6 M38 20 q2 -3 0 -6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>", "matin": "<path d=\"M14 34 A10 10 0 0 1 34 34 Z\" fill=\"#F2B544\" stroke=\"#121212\" stroke-width=\"3\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/><line x1=\"38.1\" y1=\"28.9\" x2=\"42.8\" y2=\"27.2\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"32.6\" y1=\"21.7\" x2=\"35.5\" y2=\"17.6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"24.0\" y1=\"19.0\" x2=\"24.0\" y2=\"14.0\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"15.4\" y1=\"21.7\" x2=\"12.5\" y2=\"17.6\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><line x1=\"9.9\" y1=\"28.9\" x2=\"5.2\" y2=\"27.2\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M4 34 H44\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M24 44 V38 M20 41 l4 -4 4 4\" fill=\"none\" stroke=\"#121212\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>"};
  var LOGO = {"vb": "-6 -6.0 238.5 112.0", "d": "M5.4 100.0L5.4 33.2L22.4 33.2L22.4 85.0L53.7 85.0L53.7 100.0ZM70.9 101.2Q65.8 101.2 61.8 99.4Q57.8 97.6 55.6 94.3Q53.3 91.0 53.3 86.6Q53.3 80.6 57.4 76.8Q61.4 73.1 68.9 71.1Q76.3 69.1 86.5 68.6L86.5 67.2Q86.5 63.2 84.3 61.6Q82.1 60.0 78.3 60.0Q75.5 60.0 73.2 61.4Q70.9 62.9 70.1 65.4L56.1 60.6Q58.6 55.7 64.5 52.3Q70.4 48.9 79.2 48.9Q90.2 48.9 96.3 53.6Q102.4 58.4 102.4 68.8L102.4 81.5Q102.4 85.0 102.6 88.5Q102.8 92.1 103.2 95.1Q103.6 98.1 104.1 100.0L88.6 100.0L86.9 94.1Q84.2 98.2 80.1 99.7Q75.9 101.2 70.9 101.2ZM76.7 90.1Q79.7 90.1 81.9 89.2Q84.1 88.3 85.3 86.0Q86.5 83.7 86.5 79.6L86.5 78.3Q77.5 78.8 74.1 80.7Q70.6 82.5 70.6 85.2Q70.6 87.4 72.4 88.8Q74.1 90.1 76.7 90.1ZM112.0 100.0L112.0 62.9L103.8 62.9L103.8 50.4L112.0 50.4L112.0 43.6Q112.0 37.5 114.2 34.2Q116.3 30.9 120.8 29.5Q125.3 28.2 132.2 28.2L139.4 28.2L139.4 41.1L135.4 41.1Q131.2 41.1 129.9 41.8Q128.5 42.6 128.5 45.3L128.5 50.4L139.4 50.4L139.4 62.9L128.5 62.9L128.5 100.0ZM153.0 100.0L153.0 62.8L144.4 62.8L144.4 50.4L169.6 50.4L169.6 100.0ZM190.0 101.2Q184.9 101.2 180.9 99.4Q176.9 97.6 174.7 94.3Q172.4 91.0 172.4 86.6Q172.4 80.6 176.5 76.8Q180.5 73.1 188.0 71.1Q195.4 69.1 205.6 68.6L205.6 67.2Q205.6 63.2 203.4 61.6Q201.2 60.0 197.4 60.0Q194.6 60.0 192.3 61.4Q190.0 62.9 189.2 65.4L175.2 60.6Q177.7 55.7 183.6 52.3Q189.5 48.9 198.3 48.9Q209.3 48.9 215.4 53.6Q221.5 58.4 221.5 68.8L221.5 81.5Q221.5 85.0 221.7 88.5Q221.9 92.1 222.3 95.1Q222.7 98.1 223.2 100.0L207.7 100.0L206.0 94.1Q203.3 98.2 199.2 99.7Q195.0 101.2 190.0 101.2ZM195.8 90.1Q198.8 90.1 201.0 89.2Q203.2 88.3 204.4 86.0Q205.6 83.7 205.6 79.6L205.6 78.3Q196.6 78.8 193.2 80.7Q189.7 82.5 189.7 85.2Q189.7 87.4 191.5 88.8Q193.2 90.1 195.8 90.1Z", "c": ["160.4", "29.5", "13.8"]};

  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(' '); }
  function svgRaw(inner, vb, size, label, cls) {
    var a = { className: cls, width: size, height: size, viewBox: vb, xmlns: 'http://www.w3.org/2000/svg', dangerouslySetInnerHTML: { __html: inner } };
    if (label) { a.role = 'img'; a['aria-label'] = label; } else { a['aria-hidden'] = 'true'; a.focusable = 'false'; }
    return h('svg', a);
  }

  /* ---------- Icon (Phosphor, bold / duotone) ---------- */
  function Icon(p) {
    var name = p.duotone ? 'd:' + p.name : p.name;
    var inner = ICONS[name] || ICONS[p.name] || '';
    return svgRaw(inner, '0 0 256 256', p.size || 24, p.label, cx('lf-icon', p.className));
  }

  /* ---------- Picto (custom Lafia pictograms) ---------- */
  var PICTO_LABELS = { 'matin': 'Matin', 'midi': 'Midi', 'soir': 'Soir', 'nuit': 'Nuit', 'avant-repas': 'Avant le repas', 'apres-repas': 'Après le repas', 'comprime': 'Un comprimé', 'comprime-demi': 'Un demi-comprimé', 'jours': 'Nombre de jours', 'a-payer': 'À payer', 'paye': 'Payé', 'a-retirer': 'À retirer', 'retire-partie': 'Retiré en partie', 'retire': 'Retiré', 'allergie': 'Allergie', 'urgence': 'Urgence', 'consultation': 'Qui a consulté mon dossier' };
  function Picto(p) {
    var label = p.decorative ? null : (p.label || PICTO_LABELS[p.name]);
    return svgRaw(PICTOS[p.name] || '', '0 0 48 48', p.size || 48, label, cx('lf-picto', p.className));
  }

  /* ---------- Logo ---------- */
  function Logo(p) {
    var tone = p.tone || 'royal';
    var height = p.height || 32;
    var parts = LOGO.vb.split(' ');
    var width = Math.round(height * parseFloat(parts[2]) / parseFloat(parts[3]));
    var svg = h('svg', { className: cx('lf-logo', 'lf-logo--' + tone, p.animate && 'lf-logo--animate'), width: width, height: height, viewBox: LOGO.vb, role: 'img', 'aria-label': 'Lafia' },
      h('path', { className: 'lf-logo-word', d: LOGO.d }),
      h('circle', { className: 'lf-logo-dot', cx: LOGO.c[0], cy: LOGO.c[1], r: LOGO.c[2] }));
    if (!p.href) return svg;
    return h('a', { className: 'lf-logo-link', href: p.href, 'aria-label': p.linkLabel || 'Lafia, retour au site' }, svg);
  }

  /* ---------- Button ---------- */
  function Button(p) {
    var variant = p.variant || 'primary', size = p.size || 'citizen';
    var rest = {};
    for (var k in p) if (['variant', 'size', 'icon', 'iconRight', 'loading', 'children', 'className', 'href', 'block'].indexOf(k) < 0) rest[k] = p[k];
    rest.className = cx('lf-btn', 'lf-btn--' + variant, 'lf-btn--' + size, p.block && 'lf-btn--block', p.loading && 'is-loading', p.className);
    if (p.loading) { rest['aria-busy'] = 'true'; rest.disabled = true; }
    var kids = [
      p.icon ? h(Icon, { key: 'i', name: p.icon, size: size === 'pro' ? 20 : 24 }) : null,
      h('span', { key: 'l', className: 'lf-btn-label' }, p.children),
      p.iconRight ? h(Icon, { key: 'r', name: p.iconRight, size: size === 'pro' ? 20 : 24 }) : null
    ];
    if (p.href) { rest.href = p.href; return h('a', rest, kids); }
    if (!rest.type) rest.type = 'button';
    return h('button', rest, kids);
  }

  /* ---------- Field wrapper ---------- */
  function Field(p) {
    return h('div', { className: cx('lf-field', 'lf-field--' + (p.size || 'citizen'), p.error && 'has-error', p.className) },
      h('label', { className: 'lf-field-label', htmlFor: p.id }, p.label),
      p.hint ? h('p', { className: 'lf-field-hint', id: p.id + '-hint' }, p.hint) : null,
      p.children,
      p.error ? h('p', { className: 'lf-field-error', id: p.id + '-err', role: 'alert' }, h(Icon, { name: 'warning-octagon', size: 20 }), h('span', null, p.error)) : null);
  }
  function describedBy(id, p) { return [p.hint && id + '-hint', p.error && id + '-err'].filter(Boolean).join(' ') || undefined; }

  /* ---------- TextInput ---------- */
  function TextInput(p) {
    var auto = useId(); var id = p.id || auto;
    var rest = {};
    for (var k in p) if (['label', 'hint', 'error', 'size', 'icon', 'className'].indexOf(k) < 0) rest[k] = p[k];
    rest.id = id; rest.className = 'lf-input'; rest['aria-invalid'] = p.error ? 'true' : undefined; rest['aria-describedby'] = describedBy(id, p);
    return h(Field, { id: id, label: p.label, hint: p.hint, error: p.error, size: p.size, className: p.className },
      h('div', { className: 'lf-input-wrap' }, p.icon ? h(Icon, { name: p.icon, size: 20, className: 'lf-input-icon' }) : null, h('input', rest)));
  }

  /* ---------- NpiField ---------- */
  /* NPI : 13 chiffres, groupés 4-3-3-3 pour la lecture à voix haute (0000 001 317 462). */
  var NPI_LEN = 13, NPI_GROUPS = [4, 3, 3, 3];
  function groupNpi(d) { var out = [], i = 0; NPI_GROUPS.forEach(function (n) { if (i < d.length) out.push(d.slice(i, i + n)); i += n; }); return out.join(' '); }
  function NpiField(p) {
    var auto = useId(); var id = p.id || auto;
    var controlled = p.value !== undefined;
    var st = useState(p.defaultValue || ''); var inner = st[0], setInner = st[1];
    var digits = (controlled ? p.value : inner).replace(/\D/g, '').slice(0, NPI_LEN);
    var complete = digits.length === NPI_LEN;
    var prev = useRef(complete);
    useEffect(function () { if (complete && !prev.current && p.onComplete) p.onComplete(digits); prev.current = complete; }, [complete]);
    function change(e) { var d = e.target.value.replace(/\D/g, '').slice(0, NPI_LEN); if (!controlled) setInner(d); if (p.onChange) p.onChange(d); }
    return h(Field, { id: id, label: p.label || 'NPI', hint: p.hint, error: p.error, size: p.size, className: cx('lf-npi', complete && 'is-complete', p.className) },
      h('div', { className: 'lf-input-wrap' },
        h(Icon, { name: 'identification-card', size: 24, className: 'lf-input-icon' }),
        h('input', { id: id, className: 'lf-input lf-input--id', inputMode: 'numeric', autoComplete: 'off', placeholder: '0000 000 000 000', value: groupNpi(digits), onChange: change, autoFocus: p.autoFocus, 'aria-invalid': p.error ? 'true' : undefined, 'aria-describedby': describedBy(id, p) }),
        h('span', { className: 'lf-npi-state', 'aria-live': 'polite' }, complete ? h(Icon, { name: 'check', size: 20, label: 'NPI complet' }) : h('span', { className: 'lf-npi-count' }, digits.length + '/' + NPI_LEN))));
  }

  /* ---------- CodeField ---------- */
  function CodeField(p) {
    var auto = useId(); var id = p.id || auto;
    var len = p.length || 6;
    var controlled = p.value !== undefined;
    var st = useState(p.defaultValue || ''); var inner = st[0], setInner = st[1];
    var v = (controlled ? p.value : inner).toUpperCase().replace(/[^0-9A-Z]/g, '').slice(0, len);
    var fs = useState(false);
    function change(e) { var d = e.target.value.toUpperCase().replace(/[^0-9A-Z]/g, '').slice(0, len); if (!controlled) setInner(d); if (p.onChange) p.onChange(d); }
    var cells = [];
    for (var i = 0; i < len; i++) cells.push(h('span', { key: i, className: cx('lf-code-cell', v[i] && 'is-filled', fs[0] && i === Math.min(v.length, len - 1) && 'is-caret') }, v[i] || ''));
    return h(Field, { id: id, label: p.label || 'Code carnet', hint: p.hint, error: p.error, size: p.size, className: cx('lf-code', p.className) },
      h('div', { className: 'lf-code-row' },
        h('input', { id: id, className: 'lf-code-input', value: v, onChange: change, maxLength: len, inputMode: p.numeric ? 'numeric' : 'text', autoComplete: 'one-time-code', autoCapitalize: 'characters', onFocus: function () { fs[1](true); }, onBlur: function () { fs[1](false); }, 'aria-invalid': p.error ? 'true' : undefined, 'aria-describedby': describedBy(id, p) }),
        h('div', { className: 'lf-code-cells', 'aria-hidden': 'true' }, cells)));
  }

  /* ---------- StatusBadge ---------- */
  var STATUS = {
    'apayer': { tone: 'apayer', picto: 'a-payer', label: 'À payer' },
    'paye': { tone: 'paye', picto: 'paye', label: 'Payé' },
    'aretirer': { tone: 'aretirer', picto: 'a-retirer', label: 'À retirer' },
    'partiel': { tone: 'partiel', picto: 'retire-partie', label: 'Retiré en partie' },
    'retire': { tone: 'retire', picto: 'retire', label: 'Retiré' },
    'allergie': { tone: 'danger', picto: 'allergie', label: 'Allergie' },
    'urgence': { tone: 'danger', picto: 'urgence', label: 'Urgence' },
    'encours': { tone: 'aretirer', icon: 'heartbeat', label: 'Cas en cours' },
    'termine': { tone: 'retire', icon: 'check', label: 'Cas terminé' },
    'attente': { tone: 'apayer', icon: 'flask', label: 'Analyse en attente' },
    'resultat': { tone: 'paye', icon: 'test-tube', label: 'Résultat disponible' }
  };
  function StatusBadge(p) {
    var s = STATUS[p.status] || STATUS.apayer;
    var size = p.size || 'citizen';
    var mark = s.picto && size !== 'pro' ? h(Picto, { name: s.picto, size: size === 'large' ? 40 : 28, decorative: true }) : h(Icon, { name: s.icon || 'info', size: size === 'pro' ? 16 : 20 });
    if (s.picto && size === 'pro') mark = h(Picto, { name: s.picto, size: 20, decorative: true });
    return h('span', { className: cx('lf-badge', 'lf-tone-' + s.tone, 'lf-badge--' + size, p.className) }, mark, h('span', null, p.label || s.label));
  }

  /* ---------- OrdonnanceLine ---------- */
  function fcfa(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' FCFA'; }
  function Posology(p) {
    var items = [];
    (p.moments || []).forEach(function (m) { items.push(h('span', { key: m, className: 'lf-poso-item' }, h(Picto, { name: m, size: p.size || 36 }), h('span', { className: 'lf-poso-cap' }, PICTO_LABELS[m]))); });
    if (p.meal) items.push(h('span', { key: 'meal', className: 'lf-poso-item' }, h(Picto, { name: p.meal === 'avant' ? 'avant-repas' : 'apres-repas', size: p.size || 36 }), h('span', { className: 'lf-poso-cap' }, p.meal === 'avant' ? 'Avant repas' : 'Après repas')));
    if (p.count) items.push(h('span', { key: 'n', className: 'lf-poso-item' }, h('span', { className: 'lf-poso-count' }, h(Picto, { name: p.count === 0.5 ? 'comprime-demi' : 'comprime', size: p.size || 36 }), h('b', null, '×' + (p.count === 0.5 ? '½' : p.count))), h('span', { className: 'lf-poso-cap' }, p.count === 0.5 ? '½ comprimé' : p.count + (p.count > 1 ? ' comprimés' : ' comprimé'))));
    if (p.days) items.push(h('span', { key: 'd', className: 'lf-poso-item' }, h('span', { className: 'lf-poso-count' }, h(Picto, { name: 'jours', size: p.size || 36 }), h('b', null, p.days)), h('span', { className: 'lf-poso-cap' }, p.days + ' jours')));
    return h('div', { className: 'lf-poso' }, items);
  }
  function OrdonnanceLine(p) {
    var mode = p.mode || 'citoyen';
    var auto = useId();
    var selectable = mode !== 'citoyen' && !p.disabled && p.onToggle;
    var head = h('div', { className: 'lf-line-main' },
      h('div', { className: 'lf-line-name' }, p.name),
      p.detail ? h('div', { className: 'lf-line-detail' }, p.detail) : null,
      p.posology && mode === 'citoyen' ? h(Posology, p.posology) : null,
      p.allergy ? h('div', { className: 'lf-line-allergy' }, h(Picto, { name: 'allergie', size: 20, decorative: true }), h('span', null, p.allergy)) : null);
    var side = h('div', { className: 'lf-line-side' },
      p.price != null ? h('div', { className: 'lf-line-price' }, fcfa(p.price)) : null,
      p.status ? h(StatusBadge, { status: p.status, size: mode === 'citoyen' ? 'citizen' : 'pro' }) : null);
    var cls = cx('lf-line', 'lf-line--' + mode, p.checked && 'is-checked', p.disabled && 'is-disabled', p.allergy && 'has-allergy', p.className);
    if (mode === 'citoyen') return h('div', { className: cls }, head, side);
    return h('label', { className: cls, htmlFor: auto },
      h('input', { id: auto, type: 'checkbox', className: 'lf-check', checked: !!p.checked, disabled: p.disabled || !p.onToggle, onChange: function () { if (p.onToggle) p.onToggle(!p.checked); } }),
      h('span', { className: 'lf-check-box', 'aria-hidden': 'true' }, h(Icon, { name: 'check', size: 16 })),
      head, side);
  }

  /* ---------- TimelineItem (le fil) ---------- */
  function TimelineItem(p) {
    var state = p.state || 'done';
    return h('li', { className: cx('lf-tl', 'lf-tl--' + state, p.first && 'is-first', p.last && 'is-last', p.animate && 'lf-tl--draw', p.className), style: p.index != null ? { '--lf-i': p.index } : undefined, 'aria-current': state === 'current' ? 'step' : undefined },
      h('div', { className: 'lf-tl-rail', 'aria-hidden': 'true' }, h('span', { className: 'lf-tl-fil' }), h('span', { className: 'lf-tl-node' }, p.icon ? h(Icon, { name: p.icon, size: 18 }) : null)),
      h('div', { className: 'lf-tl-body' },
        h('div', { className: 'lf-tl-meta' }, p.date ? h('time', null, p.date) : null, p.place ? h('span', null, p.place) : null),
        h('div', { className: 'lf-tl-title' }, p.title),
        p.children ? h('div', { className: 'lf-tl-content' }, p.children) : null));
  }

  /* ---------- Alert ---------- */
  var ALERT = { info: { icon: 'info' }, succes: { icon: 'check' }, attention: { icon: 'warning' }, danger: { icon: 'warning-octagon' }, allergie: { picto: 'allergie' }, urgence: { picto: 'urgence' } };
  function Alert(p) {
    var tone = p.tone || 'info'; var a = ALERT[tone] || ALERT.info;
    var strong = tone === 'allergie' || tone === 'urgence';
    return h('div', { className: cx('lf-alert', 'lf-alert--' + tone, strong && 'lf-alert--strong', p.className), role: strong || tone === 'danger' ? 'alert' : 'status' },
      h('div', { className: 'lf-alert-mark' }, a.picto ? h(Picto, { name: a.picto, size: 40, decorative: true }) : h(Icon, { name: a.icon, size: 24 })),
      h('div', { className: 'lf-alert-body' }, p.title ? h('div', { className: 'lf-alert-title' }, p.title) : null, p.children ? h('div', { className: 'lf-alert-text' }, p.children) : null, p.actions ? h('div', { className: 'lf-alert-actions' }, p.actions) : null),
      p.onClose && !strong ? h('button', { type: 'button', className: 'lf-iconbtn', onClick: p.onClose }, h(Icon, { name: 'x', size: 20, label: 'Fermer' })) : null);
  }

  /* ---------- Card ---------- */
  function Card(p) {
    var tag = p.href ? 'a' : (p.as || 'div');
    var a = { className: cx('lf-card', p.tone && 'lf-card--' + p.tone, p.interactive || p.href ? 'lf-card--interactive' : null, p.dense && 'lf-card--dense', p.className) };
    if (p.href) a.href = p.href;
    if (p.loading) return h('div', { className: cx(a.className, 'is-loading'), 'aria-busy': 'true', 'aria-label': 'Chargement' }, h('span', { className: 'lf-skel lf-skel--title' }), h('span', { className: 'lf-skel' }), h('span', { className: 'lf-skel lf-skel--short' }));
    return h(tag, a, p.children);
  }

  /* ---------- Table ---------- */
  function Table(p) {
    var cols = p.columns || [];
    return h('div', { className: cx('lf-table-wrap', p.className) },
      h('table', { className: cx('lf-table', p.dense && 'lf-table--dense') },
        p.caption ? h('caption', null, p.caption) : null,
        h('thead', null, h('tr', null, cols.map(function (c) { return h('th', { key: c.key, scope: 'col', className: c.align === 'end' ? 'is-end' : undefined }, c.label); }))),
        h('tbody', null, p.loading ? [0, 1, 2].map(function (i) { return h('tr', { key: i, 'aria-hidden': 'true' }, cols.map(function (c) { return h('td', { key: c.key }, h('span', { className: 'lf-skel' })); })); }) :
          (p.rows || []).length === 0 ? h('tr', null, h('td', { colSpan: cols.length, className: 'lf-table-empty' }, p.empty || 'Aucune donnée.')) :
          p.rows.map(function (r, i) { return h('tr', { key: r.id || i, className: r.selected ? 'is-selected' : undefined, 'aria-selected': r.selected ? 'true' : undefined }, cols.map(function (c) { return h('td', { key: c.key, className: cx(c.align === 'end' && 'is-end', c.mono && 'is-mono') }, r[c.key]); })); }))));
  }

  /* ---------- SiteHeader ---------- */
  function SiteHeader(p) {
    var links = p.links || [{ label: 'Vision', href: '#vision' }, { label: 'Comment ça marche', href: '#comment' }, { label: 'Services', href: '#services' }, { label: 'Demain', href: '#demain' }];
    var st = useState(false);
    return h('header', { className: cx('lf-siteheader', p.sticky !== false && 'is-sticky') },
      h('div', { className: 'lf-siteheader-in' },
        h(Logo, { height: 32, href: p.homeHref || '/', linkLabel: 'Lafia, accueil' }),
        h('nav', { className: cx('lf-siteheader-nav', st[0] && 'is-open'), 'aria-label': 'Sections', id: 'lf-nav' }, links.map(function (l) { return h('a', { key: l.href, href: l.href }, l.label); })),
        h(Button, { variant: 'primary', size: 'citizen', href: p.ctaHref || 'https://citoyen.lafia.stephanebah.page', icon: 'identification-card', className: 'lf-siteheader-cta' }, p.ctaLabel || 'Ouvrir mon carnet'),
        h('button', { type: 'button', className: 'lf-iconbtn lf-siteheader-menu', 'aria-expanded': st[0] ? 'true' : 'false', 'aria-controls': 'lf-nav', onClick: function () { st[1](!st[0]); } }, h(Icon, { name: st[0] ? 'x' : 'list', size: 24, label: 'Menu' }))));
  }

  /* ---------- SiteFooter ---------- */
  var APPS = [
    { key: 'citoyen', label: 'Carnet citoyen', addr: 'citoyen.lafia.stephanebah.page' },
    { key: 'soin', label: 'Soin', addr: 'soin.lafia.stephanebah.page' },
    { key: 'caisse', label: 'Caisse', addr: 'caisse.lafia.stephanebah.page' },
    { key: 'pharmacie', label: 'Pharmacie', addr: 'pharmacie.lafia.stephanebah.page' }];
  function SiteFooter(p) {
    return h('footer', { className: 'lf-sitefooter' },
      h('div', { className: 'lf-sitefooter-in' },
        h('div', { className: 'lf-sitefooter-brand' }, h(Logo, { tone: 'blanc', height: 36 }), h('p', null, p.note || 'Prototype de démonstration : toutes les données sont fictives.')),
        h('nav', { 'aria-label': 'Applications' }, h('ul', null, APPS.map(function (a) { return h('li', { key: a.key }, h('a', { href: 'https://' + a.addr }, h('span', null, a.label), h('span', { className: 'lf-mono' }, a.addr))); }))),
        h('a', { className: 'lf-sitefooter-gh', href: 'https://github.com/StephaneBah/Lafia' }, h(Icon, { name: 'github-logo', size: 20 }), h('span', null, 'Code source sur GitHub'))));
  }

  /* ---------- AppHeader ---------- */
  var ACTORS = { citoyen: { label: 'Carnet citoyen', icon: 'user' }, soin: { label: 'Soin', icon: 'stethoscope' }, caisse: { label: 'Caisse', icon: 'cash-register' }, pharmacie: { label: 'Pharmacie', icon: 'pill' } };
  function AppHeader(p) {
    var a = ACTORS[p.actor] || ACTORS.soin;
    return h('header', { className: cx('lf-appheader', p.actor === 'citoyen' && 'lf-appheader--citizen') },
      h(Logo, { tone: 'blanc', height: 26, href: p.siteHref || 'https://lafia.stephanebah.page' }),
      h('span', { className: 'lf-appheader-actor' }, h(Icon, { name: a.icon, size: 20 }), h('span', null, p.actorLabel || a.label)),
      p.place ? h('span', { className: 'lf-appheader-place' }, p.place) : null,
      h('span', { className: 'lf-appheader-spacer' }),
      p.user ? h('span', { className: 'lf-appheader-user' }, h(Icon, { name: 'user', size: 20 }), h('span', null, p.user)) : null,
      p.onSignOut ? h('button', { type: 'button', className: 'lf-appheader-out', onClick: p.onSignOut }, h(Icon, { name: 'sign-out', size: 20 }), h('span', null, 'Se déconnecter')) : null);
  }

  /* ---------- DemoAccount ---------- */
  function copyText(t) {
    try { if (navigator.clipboard) return navigator.clipboard.writeText(t); } catch (e) {}
    var ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); } catch (e) {} document.body.removeChild(ta); return Promise.resolve();
  }
  function CopyRow(p) {
    var st = useState(false);
    function go() { Promise.resolve(copyText(p.value)).then(function () { st[1](true); setTimeout(function () { st[1](false); }, 1600); }, function () {}); }
    return h('div', { className: 'lf-demo-row' },
      h('span', { className: 'lf-demo-k' }, p.label),
      h('code', { className: 'lf-demo-v' }, p.value),
      h('button', { type: 'button', className: cx('lf-copy', st[0] && 'is-done'), onClick: go }, h(Icon, { name: st[0] ? 'check' : 'copy', size: 18 }), h('span', { 'aria-live': 'polite' }, st[0] ? 'Copié' : 'Copier')));
  }
  function DemoAccount(p) {
    return h('details', { className: 'lf-demo', open: p.open },
      h('summary', null, h(Icon, { name: 'lock-simple', size: 20 }), h('span', null, p.summary || 'Essayer avec un compte de démonstration'), h(Icon, { name: 'caret-down', size: 18, className: 'lf-demo-caret' })),
      h('div', { className: 'lf-demo-body' },
        h(CopyRow, { label: p.identifierLabel || 'Identifiant', value: p.identifier || 'medecin.mel' }),
        p.password === false ? null : h(CopyRow, { label: p.passwordLabel || 'Mot de passe', value: p.password || 'lafia-demo' }),
        p.note ? h('p', { className: 'lf-demo-note' }, p.note) : null));
  }

  /* ---------- ServiceCard ---------- */
  function ServiceCard(p) {
    var a = ACTORS[p.actor] || ACTORS.soin;
    var addr = p.address || (APPS.filter(function (x) { return x.key === p.actor; })[0] || {}).addr;
    var href = p.href || 'https://' + addr;
    return h('div', { className: 'lf-service' },
      h('a', { className: 'lf-service-card', href: href },
        h('div', { className: 'lf-service-illu', 'aria-hidden': 'true' }, p.illustration || h(Icon, { name: a.icon, duotone: true, size: 72 })),
        h('div', { className: 'lf-service-for' }, p.forWhom),
        h('div', { className: 'lf-service-title' }, p.title || a.label),
        h('p', { className: 'lf-service-desc' }, p.description),
        h('div', { className: 'lf-service-foot' }, h('span', { className: 'lf-mono lf-service-addr' }, addr), h('span', { className: 'lf-service-open' }, h('span', null, 'Ouvrir'), h(Icon, { name: 'arrow-square-out', size: 20 })))),
      p.demo === false ? null : h(DemoAccount, p.demo || {}));
  }

  /* ---------- SoonCard ---------- */
  function SoonCard(p) {
    return h('article', { className: 'lf-soon' },
      h('div', { className: 'lf-soon-top' }, h('span', { className: 'lf-soon-icon', 'aria-hidden': 'true' }, h(Icon, { name: p.icon || 'plus', duotone: true, size: 32 })), h('span', { className: 'lf-soon-badge' }, 'Bientôt')),
      h('h3', { className: 'lf-soon-title' }, p.title),
      p.tagline ? h('p', { className: 'lf-soon-tag' }, p.tagline) : null,
      p.children ? h('p', { className: 'lf-soon-desc' }, p.children) : null);
  }

  window.Lafia = { Logo: Logo, Icon: Icon, Picto: Picto, Posology: Posology, Button: Button, TextInput: TextInput, NpiField: NpiField, CodeField: CodeField, StatusBadge: StatusBadge, OrdonnanceLine: OrdonnanceLine, TimelineItem: TimelineItem, Alert: Alert, Card: Card, Table: Table, SiteHeader: SiteHeader, SiteFooter: SiteFooter, AppHeader: AppHeader, ServiceCard: ServiceCard, DemoAccount: DemoAccount, SoonCard: SoonCard, formatFcfa: fcfa, formatNpi: groupNpi };
})();
