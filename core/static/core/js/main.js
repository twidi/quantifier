document.addEventListener('DOMContentLoaded', () => {

    // when a details element is opened, close the other ones having the same data-group attribute, if any
    // and make it visible
    document.addEventListener('toggle', ev => {
        if (ev.target.nodeName !== 'DETAILS' || !ev.target.open) {
            return;
        }
        const group = ev.target.getAttribute('data-group');
        if (group) {
            document.querySelectorAll('details[data-group="' + group + '"][open]').forEach(el => {
                if (el !== ev.target) {
                    el.open = false;
                }
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
    const create_all_select2 = elt => elt.querySelectorAll('select.autocomplete').forEach(elt => {
        create_select2(elt);
    })
    document.addEventListener('toggle', ev => {
        if (ev.target.nodeName === 'DETAILS') {
            create_all_select2(ev.target);
        }
    }, true);
    // create select2 elements on focus
    document.addEventListener("focusin", ev => {
        if (ev.target.nodeName !== 'SELECT' || !ev.target.classList.contains('autocomplete')) {
            return;
        }
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
        if (el.nodeName !== 'INPUT' || !el.classList.contains('type-ahead')) {
            return;
        }
        const listener = ev => filter_quick_categories(el.value, document.querySelector(el.getAttribute('data-type-ahead-list')), el.getAttribute('data-type-ahead-list-item-selector'), el.getAttribute('data-type-ahead-text-selector'));
        el.addEventListener('keyup', listener);
        el.addEventListener('focusout', ev => ev.target.removeEventListener('keyup', listener), {once: true});
    };
    document.addEventListener('focusin', ev => on_focusin(ev.target));
    let typeahead_with_focus = document.querySelector('input.type-ahead:focus');
    if (typeahead_with_focus) {
        on_focusin(typeahead_with_focus);
    }
    document.body.classList.add('typehead-active');

    // when a details element is opened, allow to hit the escape key to close it
    document.addEventListener('toggle', ev => {
        if (ev.target.nodeName !== 'DETAILS' || !ev.target.open || !ev.target.classList.contains('as-dropdown')) {
            return;
        }
        const details = ev.target;
        const escape_listener = ev => {
            if (ev.key === 'Escape') {
                details.querySelector('summary').click();
                ev.preventDefault();
            }
        }
        window.addEventListener('keyup', escape_listener);
        const close_listener = ev => {
            if (details.open) {
                return;
            }
            window.removeEventListener('keyup', escape_listener);
            details.removeEventListener('toggle', close_listener);
        }
        details.addEventListener('toggle', close_listener);
    }, true);

    // animate the closing of the details element, and allow closing it by dragging the handle
    document.addEventListener('toggle', ev => {
        if (ev.target.nodeName !== 'DETAILS' || !ev.target.open || !ev.target.classList.contains('as-dropdown') || !ev.target.querySelector(':scope > .card.details-dropdown.large-details')) {
            return;
        }
        const details = ev.target, summary = details.querySelector('summary'),
            card = details.querySelector(':scope > .card');

        // animate the closing of the details element (for this we need to intercept the click on the summary element,
        // set a temporary class on the details to trigger the animation, and really close the details at the end of the animation)
        const animate_and_close = () => {
            details.classList.add('closing');
            const transition_listener = ev => {
                if (ev.target !== card || ev.propertyName !== 'transform') {
                    return;
                }
                details.open = false;
                details.classList.remove('closing');
                card.style.removeProperty('height');
                details.removeEventListener('transitionend', transition_listener);
            }
            details.addEventListener('transitionend', transition_listener);
        }
        const summary_click_listener = ev => {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            if (!card.classList.contains('closing-by-dragging')) {
                animate_and_close();
            }
        }
        summary.addEventListener('click', summary_click_listener);

        // allow closing it by dragging the handle
        if (Hammer) {
            const handle_position = getComputedStyle(card).getPropertyValue('--handle-position');
            const drag_from_top = handle_position === 'top';
            if (!summary.classList.contains('close-by-dragging-ready')) {
                summary.classList.add('close-by-dragging-ready');
                const hammer = new Hammer(summary);
                hammer.get('pan').set({direction: Hammer.DIRECTION_VERTICAL});
                hammer.get('swipe').set({direction: drag_from_top ? Hammer.DIRECTION_DOWN : Hammer.DIRECTION_UP});
                let height = null, drag_done = false;

                function start_drag() {
                    drag_done = false;
                    height = card.offsetHeight;
                    card.classList.add('closing-by-dragging');
                }

                function end_drag(close) {
                    drag_done = true;
                    if (close) {
                        animate_and_close();
                    } else {
                        card.style.removeProperty('height');
                    }
                    setTimeout(() => card.classList.remove('closing-by-dragging'), 500);
                }

                hammer.on('swipe', ev => end_drag(true));
                hammer.on('pan', ev => {
                    const delta = drag_from_top ? Math.max(0, ev.deltaY) : Math.min(0, ev.deltaY);
                    if (height === null) {
                        start_drag();
                    }
                    card.style.setProperty('height', `${height - (drag_from_top ? delta : -delta)}px`);
                    if (ev.isFinal) {
                        if (!drag_done) {
                            end_drag(Math.abs(delta) > height / 2);
                        }
                        drag_done = false; // allow to drag again
                        height = null;
                    }
                });
            }
        }

        const close_listener = ev => {
            if (details.open) {
                return;
            }
            summary.removeEventListener('click', summary_click_listener);
            details.removeEventListener('toggle', close_listener);
        }
        details.addEventListener('toggle', close_listener);
    }, true);

});
