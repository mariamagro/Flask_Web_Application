
$(document).ready(function () {
    
    // Ratings functionality
    const ratingForms = $('.ratings');

    ratingForms.each(function () {
        // get the necessary attributes
        const form = $(this);
        const stars = form.find('.rating .star');
        const recipeId = form.find('#recipeId').val();
        const userId = form.find('#userId').val();
        let userRating = null;

        // take the user rating from the database (server)
        $.ajax({
            url: `/get_user_rating/${userId}/${recipeId}`,
            method: 'GET',
            success: function (data) {
                userRating = data.userRating;
                // check that the user has rated the recipe
                if (userRating !== null) {
                    // color the stars if the user has already rated the recipes
                    // make the selected stars belong to the class 'selected'
                    stars.slice(0, userRating).addClass('selected');
                }

                // color the stars according to the CSS when the user hovers over them
                stars.hover(
                    function () {
                        const ratingValue = $(this).data('rating');
                        stars.removeClass('selected');
                        // color all the stars with lower values than the star the user is hovering over
                        stars.filter(`:lt(${ratingValue})`).addClass('selected');
                    },
                    function () {
                        // revert to the previous rating if the user stops hovering over the stars
                        stars.removeClass('selected');
                        stars.filter(`:lt(${userRating})`).addClass('selected');
                    }
                );

                // color the stars when the user rates the recipe
                stars.click(function () {
                    const ratingValue = $(this).data('rating');

                    // update hidden input field value with the selected rating value
                    form.find('input[name="rating"]').val(ratingValue);

                    // save the user rating
                    $.ajax({
                        url: '/rate_recipe/' + recipeId,
                        method: 'POST',
                        data: { rating: ratingValue },
                        success: function () {
                            // Update the average rating display if needed
                        }
                    });
                });
            }
        });
    });


    // Bookmarks functionality
    const bookmarksForms = $('.bookmarks');
    bookmarksForms.each(function () {
        // get the necessary attributes
        const form = $(this);
        const bookmarkButton = form.find('.bookmark');
        const recipeId = form.find('#recipeId').val();
        const userId = form.find('#userId').val();

        // retrieve whether the user is authenticated
        const isAuthenticated = bookmarkButton.data('auth') === 'True';


        if (isAuthenticated) {
            // since the user is authenticated, check if the recipe has alerady being bookmarked by the user and update the results
            $.get(`/get_bookmark_status/${userId}/${recipeId}`, function (response) {
                const isBookmarked = response.bookmarked;
                bookmarkButton.toggleClass('bookmarked', isBookmarked);
            });

            // color the bookmark button when the user clicks on it
            bookmarkButton.click(function () {
                // toggle the 'bookmarked' class and update the results in the database (if the bookmark is selected, then it belong to class 'bookmarked')
                const isBookmarked = bookmarkButton.hasClass('bookmarked');
                bookmarkButton.toggleClass('bookmarked', !isBookmarked);

                // update the hidden input field value  with the selected bookmark value
                form.find('input[name="bookmark"]').val(bookmarkButton.hasClass('bookmarked') ? 1 : 0);

                // save the user's bookmark in local storage so that it can later be displayed
                localStorage.setItem(`userBookmark_${recipeId}`, bookmarkButton.hasClass('bookmarked') ? '1' : '0');

                // save the value of the bookmark in the database (server)
                updateBookmarkStatus(bookmarkButton.hasClass('bookmarked') ? 1 : 0).then(function(response) {
                    console.log(response); 
                });
            });
        } else {
            // if the user is not authenticated, then the 'bookmarked' class will not be present
            bookmarkButton.removeClass('bookmarked');
        }
    });

    // return the results from the search filter
    // this gets the value of the element with if searchInput and attaches an event listener for both the 'keyup' (when user types a key) 
    // and 'change' (when user changes the input value) events
    $('#searchInput').on('keyup change', function () {
        // get the value of the input of the user
        var query = $(this).val();
        $.ajax({
          // specify the url to which the request is sent 
          url: '/search/results', 
          // request method
          type: 'GET',
          // send a parameter 'q' with the variable query as its value
          data: { q: query },
          // specifies the expected type of the response
          dataType: 'html',
          // if the request is successful, then retrieve the results
          success: function (data) {
            console.log(data)
            $('#results').html(data);
          }
        });
    });
    

});


// Functions for the photo gallery 

let currentImageIndex = 0;

// this opens the gallery of images
function openGallery(imgElement) {
    // obtain all the images
    const gallery = document.getElementById('gallery');
    // obtain a specific image of the gallery
    const galleryImg = document.getElementById('image-gallery');

    // check that the clicked image belongs to the photo-gallery class
    if ($(imgElement).closest('.photo-gallery').length > 0) {
        // this makes visible the image with the CSS properties established for it
        gallery.style.display = 'block';
        // the image displayed in the gallery is updated every time the user clicks on it
        galleryImg.src = imgElement.src;
    }
}

// this function closes the gallery of photos
function closeGallery() {
    // gets the image that is being displayed and if the user selects the 'close' arrow, it displays 'none'
    const gallery = document.getElementById('gallery');
    gallery.style.display = 'none';
}

// this function changes the photos of the gallery each time the user clicks the 'next' arrow
function changeImage(step) {
    // get the image that is being displayed
    const galleryImg = document.getElementById('image-gallery');
    // get all the images that belong to the class 'photo'
    const images = document.querySelectorAll('.photo');
    // this gets the counter/number of the image
    const counter = document.getElementById('image-counter');

    // if there are no images to display, then it will not display anything
    if (images.length === 0) {
        return; 
    }

    // add the step every time the user changes from one image to the other
    currentImageIndex += step;

    // if the user is in the last image and he/she clicks the 'next' arrow, then it will display the first image of all
    if (currentImageIndex >= images.length) {
        currentImageIndex = 0;
    // if the user clicks the 'previous' arrow, then it will display the previous image
    } else if (currentImageIndex < 0) {
        currentImageIndex = images.length - 1;
    }
    // this updates the source of the image that is being displayed
    galleryImg.src = Array.from(images)[currentImageIndex].src;
    // this updates the counter, so that the right value is displayed
    counter.textContent = `${currentImageIndex + 1}/${images.length}`;
}


// Functions for submitting images

// this function gets the element with the specified 'id' when the user clicks on it and displays the possible filed to upload
function triggerFileInput(type) {
    document.getElementById(`${type}-photo-input`).click();
}

// this function allows the user to upload a profile photo by submitting the image once the user selects it 
function uploadProfilePhoto() {
    const form = document.getElementById('profile-photo-form');
    form.submit();
}

// this function allows the user to upload a background photo by submitting the image once the user selects it 
function uploadBackgroundPhoto() {
    const form = document.getElementById('background-photo-form');
    form.submit();
}

// this function allows the users to upload the photos they want of a specific recipe by submitting the image once the user selects it
function photoInput(){
    document.getElementById("file-input").addEventListener("change", function () {
        document.getElementById("upload-form").submit();
    });
}

