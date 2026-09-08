/*
 * ParameterDefaults admin: live "Parameters" panel. See admin.py
 *
 * The defaults request excludes the row being edited, so the panel always answers
 * "what would this parameter be if I did not set it here".
 */
(function () {
  'use strict';

  const NAME_TOKEN = '__NAME__';
  const DIMENSIONS = ['software', 'scope', 'cluster'];
  const PLACEHOLDER = 'Pick a processor above.';

  document.addEventListener('DOMContentLoaded', function () {
    const panel = document.getElementById('parameter-defaults-panel');
    const values = document.getElementById('id_values');
    const procSelect = document.getElementById('id_proc_software');
    if (!panel || !values || !procSelect) return;

    const processors = JSON.parse(panel.dataset.processors);
    const selects = DIMENSIONS.map((d) => document.getElementById('id_' + d)).filter(Boolean);

    let schemaProps = {};
    let schemaFor = null;
    let lastDefaults = null;
    let pending = null;

    function scheduleRefresh() {
      window.clearTimeout(pending);
      pending = window.setTimeout(refresh, 50);
    }

    function processorName() {
      return processors[procSelect.value] || null;
    }

    function url(template, name, params) {
      const query = new URLSearchParams(params).toString();
      return template.replace(NAME_TOKEN, encodeURIComponent(name)) + (query ? '?' + query : '');
    }

    function currentValues() {
      try {
        const parsed = JSON.parse(values.value || '{}');
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
      } catch (e) {
        return null;
      }
    }

    async function refresh() {
      const name = processorName();
      if (!name) {
        lastDefaults = null;
        panel.textContent = PLACEHOLDER;
        return;
      }

      const params = {};
      selects.forEach((el) => {
        if (el.value) params[el.id.replace('id_', '')] = el.value;
      });
      if (panel.dataset.rowPk) params.exclude_row = panel.dataset.rowPk;

      try {
        if (schemaFor !== name) {
          const schema = await fetch(url(panel.dataset.schemaUrl, name, {})).then((r) => r.json());
          schemaProps = (schema.schema && schema.schema.properties) || {};
          schemaFor = name;
        }
        lastDefaults = await fetch(url(panel.dataset.defaultsUrl, name, params)).then((r) => r.json());
        render();
      } catch (e) {
        panel.textContent = 'Could not load parameters: ' + e;
      }
    }

    function render() {
      if (!lastDefaults) return;
      const defaults = lastDefaults;
      const here = currentValues() || {};
      const cleared = new Set(defaults.required_overrides || []);
      const rows = Object.keys(schemaProps).map((key) => {
        const prop = schemaProps[key];
        const has = Object.prototype.hasOwnProperty.call(defaults.defaults, key);
        const shown = cleared.has(key) ? 'required (cleared)' : has ? JSON.stringify(defaults.defaults[key]) : '—';
        return (
          '<tr>' +
          '<td><code>' +
          esc(key) +
          '</code></td>' +
          '<td>' +
          esc(prop.type || '—') +
          '</td>' +
          '<td><code>' +
          esc(shown) +
          '</code></td>' +
          '<td>' +
          esc(defaults.sources[key] || '') +
          '</td>' +
          '<td>' +
          (key in here ? '✓ in Values' : '<a href="#" data-add="' + esc(key) + '">Add to Values</a>') +
          '</td>' +
          '</tr>'
        );
      });
      panel.innerHTML =
        '<table class="table table-sm" style="table-layout:fixed;width:100%">' +
        '<colgroup><col style="width:18em"><col style="width:6em"><col><col style="width:8em"><col style="width:12em"></colgroup>' +
        '<tr><th>parameter</th><th>type</th><th>resolves to</th><th>source</th><th>Override this parameter</th></tr>' +
        rows.join('') +
        '</table>';

      panel.querySelectorAll('a[data-add]').forEach((a) => {
        a.addEventListener('click', (ev) => {
          ev.preventDefault();
          addKey(a.dataset.add);
        });
      });
    }

    function addKey(key) {
      const current = currentValues();
      if (current === null) {
        window.alert('Values is not a JSON object; fix it before adding keys.');
        return;
      }
      const has = Object.prototype.hasOwnProperty.call(lastDefaults.defaults, key);
      current[key] = has ? lastDefaults.defaults[key] : null;
      values.value = JSON.stringify(current, null, 2);
      render();
    }

    function esc(text) {
      return String(text).replace(
        /[&<>"']/g,
        (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
      );
    }

    const watched = [procSelect].concat(selects);
    const jqueries = [window.jQuery, window.django && window.django.jQuery].filter(
      (jq, i, all) => jq && all.indexOf(jq) === i
    );
    jqueries.forEach((jq) => jq(watched).on('change', scheduleRefresh));
    watched.forEach((el) => el.addEventListener('change', scheduleRefresh));
    // Typing in Values only changes the "here" marks; no refetch.
    values.addEventListener('input', render);
    refresh();
  });
})();
