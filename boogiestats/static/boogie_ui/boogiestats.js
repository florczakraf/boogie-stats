const dateOptions = {
    hour: "numeric",
    minute: "numeric",
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hourCycle: "h23",
};

[...document.getElementsByClassName("convert-timestamp")].forEach(element => {
    const datetime = new Date(parseInt(element.textContent) * 1000);
    element.parentNode.innerHTML = datetime.toLocaleString("en-US", dateOptions);
})
