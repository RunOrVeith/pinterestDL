
function scroll_to_bottom(scrolls=1) {
    let html = document.documentElement;
    let obj = document.body;
    let height = Math.max(document.body.scrollHeight, document.body.offsetHeight, 
                       html.clientHeight, html.scrollHeight, html.offsetHeight );

    window.scrollTo(0, height*scrolls);
    if( obj.scrollTop !== (obj.scrollHeight - obj.offsetHeight))
    {
        scroll_to_bottom();
    }
    
}


function collect_low_res_srcs() {
    let imgs = document.getElementsByTagName("img");

    let links = document.getElementsByClassName("pinLink pinImageWrapper");
    let srcs = []; 
    
    for (var i = 0; i < links.length; i++) {
        srcs.push(links[i].href);
    }
    return srcs;
};


function collect_high_res_srcs(low_res_srcs, start_idx=0, stop_idx=low_res_srcs.length) {
    let full_res_links = [];

    function retrieve_full_res(url_idx) {

        console.log(url_idx + 1, stop_idx);
        if (url_idx < stop_idx) {

            let wind = window.open(low_res_srcs[url_idx]);
            function get_image_url() {
                ims = wind.document.getElementsByTagName("img");
                full_res_links.push(ims[ims.length - 1].src);
                wind.close();
                retrieve_full_res(url_idx+1);
            }
            wind.get_image_url = get_image_url;
            wind.addEventListener('load', wind.get_image_url, true);
        } else {
                document.write(full_res_links);
        }
        
    }

    retrieve_full_res(start_idx);
    return full_res_links;
}

function get_pinned_image_srcs(start_idx=0, stop_idx=undefined) {
    let low_srcs = collect_low_res_srcs();
    let high_srcs = collect_high_res_srcs(low_srcs, start_idx, stop_idx);
}



get_pinned_image_srcs();


// Now go to the page, right-click-> select all, CTRL+C, create a new file, CTRL+P, save the file for later.
// Run the python script
