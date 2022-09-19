// when a details element is opened, close the other ones having the same data-group attribute, if any
// and make it visible
document.addEventListener('toggle', ev => {
    if (ev.target.nodeName !== 'DETAILS' || !ev.target.open) { return; }
    const group = ev.target.getAttribute('data-group');
    if (group) {
        document.querySelectorAll('details[data-group="' + group + '"][open]').forEach(el => {
            if (el !== ev.target) { el.open = false; }
        });
    }
    if (ev.target.classList.contains('scroll-into-view')) {
        const scroll_elt_selector = ev.target.getAttribute('data-scroll-into-view');
        setTimeout(() => (scroll_elt_selector ? ev.target.querySelector(scroll_elt_selector) : ev.target)?.scrollIntoViewIfNeeded(), 50)
    }
}, true);

// focus on the first input field when a details element with "focus-first-input" class is opened
document.addEventListener('toggle', ev => {
    if (ev.target.nodeName === 'DETAILS' && ev.target.open && ev.target.classList.contains('focus-first-input')) {
        const container_selector = ev.target.getAttribute('data-focus-first-input-in');
        const input_selector = ev.target.getAttribute('data-focus-first-input') || 'input:not([type="hidden"]),select,textarea';
        (container_selector ? ev.target.querySelector(container_selector) : ev.target)?.querySelectorAll(input_selector)[0]?.focus();
    }
}, true);

// create select2 elements when details element is opened
const create_select2 = select => {
    setTimeout(() => $(select).select2({theme: 'bootstrap-5', dropdownAutoWidth: true}), 500);
};
const create_all_select2 = elt => elt.querySelectorAll('select.autocomplete').forEach(elt => { create_select2(elt); })
document.addEventListener('toggle', ev => { if (ev.target.nodeName === 'DETAILS') { create_all_select2(ev.target); } }, true);
// create select2 elements on focus
document.addEventListener("focusin", ev => {
    if (ev.target.nodeName !== 'SELECT' || !ev.target.classList.contains('autocomplete')) { return; }
    ev.preventDefault();
    ev.stopImmediatePropagation();
    create_select2(ev.target);
});

// typeahead
const filter_quick_categories = (text, list, list_item_selector, text_selector) => {
    const filter = text.toLowerCase();
    let has_hidden = false;
    list.querySelectorAll(list_item_selector).forEach(item => {
        let hidden = !(text_selector ? item.querySelector(text_selector) : item).textContent.toLowerCase().includes(filter);
        item.style.display = hidden ? 'none' : '';
        has_hidden ||= hidden;
        item.classList.toggle('type-ahead-hidden', hidden);
    });
    list.classList.toggle('type-ahead-has-hidden', has_hidden);
};
const on_focusin = el => {
    if (el.nodeName !== 'INPUT' || !el.classList.contains('type-ahead')) { return; }
    let callback = ev => filter_quick_categories(el.value, document.querySelector(el.getAttribute('data-type-ahead-list')), el.getAttribute('data-type-ahead-list-item-selector'), el.getAttribute('data-type-ahead-text-selector'));
    el.addEventListener('keyup', callback);
    el.addEventListener('focusout', ev => ev.target.removeEventListener('keyup', callback), {once: true});
};
document.addEventListener('focusin', ev => on_focusin(ev.target));
let typeahead_with_focus = document.querySelector('input.type-ahead:focus');
if (typeahead_with_focus) { on_focusin(typeahead_with_focus); }
document.body.classList.add('typehead-active');
