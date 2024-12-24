const dateOptions = {
    hour: "numeric",
    minute: "numeric",
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hourCycle: "h23",
};


function show_elements(elements) {
    for (element of elements) {
        element.classList.remove("visually-hidden");
    }
}


function process_twitch_status(player_id, elements_to_show) {
    const url = `/api/v1/live-on-twitch/${player_id}/`;

    fetch(url).then((response) => {
        response.json().then((status) => {
            if (status.is_live) {
                show_elements(elements_to_show);
            }
        });
    });
}


// --------------------------------
// Dynamically alter the site elements with the hooks below. They are based on element classes.
// At the moment we use them to display timestamps using browser's timezone and checking twitch live status.

// timestamps
[...document.getElementsByClassName("convert-timestamp")].forEach(element => {
    const datetime = new Date(parseInt(element.textContent) * 1000);
    element.parentNode.innerHTML = datetime.toLocaleString("en-US", dateOptions);
});


// twitch live status
let player_id_to_elements = {};
[...document.getElementsByClassName("check-live-status")].forEach(element => {
    const parent = element.parentNode;
    const player_id = element.textContent;
    if (player_id) {
        if (!player_id_to_elements[player_id]) {
            player_id_to_elements[player_id] = [parent];
        } else {
            player_id_to_elements[player_id].push(parent);
        }
    }
});
for (const [player_id, elements] of Object.entries(player_id_to_elements)) {
    process_twitch_status(player_id, elements)
}
