// Story Forest - Book Display Logic

// Function to get URL parameters
function getUrlParams() {
    const params = {};
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    
    for (const [key, value] of urlParams.entries()) {
        params[key] = value;
    }
    
    return params;
}

// Function to load story data
async function loadStory(storyId) {
    try {
        console.log(`Attempting to load story from: /stories/${storyId}/story.json`);
        const response = await fetch(`/stories/${storyId}/story.json`);
        
        if (!response.ok) {
            console.error(`Server responded with status: ${response.status} ${response.statusText}`);
            throw new Error(`Failed to load story: ${response.statusText} (${response.status})`);
        }
        
        const data = await response.json();
        console.log(`Successfully loaded story with ${data.length} elements`);
        return data;
    } catch (error) {
        console.error('Error loading story:', error);
        
        // Show a more detailed error message
        const errorDetails = document.createElement('div');
        errorDetails.style.padding = '20px';
        errorDetails.style.color = 'red';
        errorDetails.style.backgroundColor = '#ffeeee';
        errorDetails.style.borderRadius = '5px';
        errorDetails.style.margin = '20px';
        errorDetails.style.maxWidth = '800px';
        
        errorDetails.innerHTML = `
            <h2>Error Loading Story</h2>
            <p>${error.message}</p>
            <p>Story ID: ${storyId}</p>
            <p>This could be due to:</p>
            <ul>
                <li>The story was not generated correctly</li>
                <li>The story.json file was not saved properly</li>
                <li>The server is not correctly serving files from the stories directory</li>
            </ul>
            <p><a href="/" style="color: blue;">Return to home page</a></p>
        `;
        
        document.body.innerHTML = '';
        document.body.appendChild(errorDetails);
        return null;
    }
}

// Format the storybook pages
function formatStorybook(storyData) {
    // Get references to the DOM elements
    const swiperWrapper = document.querySelector('.swiper-wrapper');
    
    // Clear existing slides
    swiperWrapper.innerHTML = '';
    
    // Extract story metadata from the first object
    const metadata = storyData[0];
    const title = metadata.title || "Story Forest Book";
    
    // Add cover slide
    swiperWrapper.innerHTML += `
        <div class="swiper-slide page-cover" data-is-cover="true">
            <h1>${title}</h1>
            <img src="/stories/${storyId}/cover.png" alt="${title} Cover" 
                 onerror="this.onerror=null; this.src='/stories/${storyId}/pages/page_01.png';">
            <div class="author">Story Forest</div>
        </div>
    `;
    
    // Add story pages (starting from index 1 because index 0 is metadata)
    for (let i = 1; i < storyData.length; i++) {
        const page = storyData[i];
        if (page.page !== undefined) {  // It's a story page, not metadata
            // The image index should match the page number plus 1 (since image_1.png is the cover)
            const imageIndex = page.page + 1;
            
            swiperWrapper.innerHTML += `
                <div class="swiper-slide">
                    <div class="page-content">
                        <div class="page-image" style="background-image: url('/stories/${storyId}/pages/page_${page.page.toString().padStart(2, '0')}.png');"
                             onerror="handleImageError(this)"></div>
                        <div class="page-text-container">
                            <div class="page-text">${page.text}</div>
                            <div class="page-number">${page.page}</div>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    // Add back cover slide - use the last image or a placeholder
    const lastPageIndex = storyData.length;
    swiperWrapper.innerHTML += `
        <div class="swiper-slide page-cover" data-is-cover="true">
            <h1>The End</h1>
            <img src="/stories/${storyId}/pages/page_${(lastPageIndex-1).toString().padStart(2, '0')}.png" alt="The End" 
                 onerror="this.onerror=null; this.src='/stories/${storyId}/cover.png'; this.style.opacity=0.7;">
            <div class="author">Thanks for reading!</div>
        </div>
    `;
    
    // Initialize Swiper after adding all slides
    initializeSwiper();
}

// Function to handle image errors
function handleImageError(imageElement) {
    console.log('Image failed to load, setting fallback');
    imageElement.style.backgroundColor = '#f8f8f8';
    imageElement.style.backgroundImage = 'none';
    
    // Create a placeholder message
    const placeholder = document.createElement('div');
    placeholder.style.height = '100%';
    placeholder.style.display = 'flex';
    placeholder.style.alignItems = 'center';
    placeholder.style.justifyContent = 'center';
    placeholder.style.textAlign = 'center';
    placeholder.style.padding = '20px';
    placeholder.style.color = '#999';
    placeholder.innerHTML = '<p>Image not available</p>';
    
    imageElement.appendChild(placeholder);
}

// Initialize Swiper
function initializeSwiper() {
    // Preload page turn sound
    const pageSound = new Audio('https://www.soundjay.com/page-flip-sounds/page-flip-01a.mp3');
    
    // Initialize Swiper
    const swiper = new Swiper('.swiper', {
        effect: 'flip',
        flipEffect: {
            slideShadows: true,
            limitRotation: true
        },
        navigation: {
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
        },
        keyboard: {
            enabled: true,
        },
        mousewheel: true,
        speed: 800,
        grabCursor: true,
        on: {
            slideChangeTransitionStart: function() {
                pageSound.currentTime = 0;
                pageSound.play().catch(e => console.log('Audio play failed:', e));
            },
            slideChangeTransitionEnd: function() {
                updateSpineVisibility();
            },
            init: function() {
                updateSpineVisibility();
            }
        }
    });
}

// Function to update spine visibility based on current slide
function updateSpineVisibility() {
    const spine = document.getElementById('bookSpine');
    const activeSlide = document.querySelector('.swiper-slide-active');
    if (!activeSlide) return;
    
    const isCover = activeSlide.getAttribute('data-is-cover') === 'true';
    
    if (isCover) {
        // Show spine and position it correctly on cover slides
        const slideRect = activeSlide.getBoundingClientRect();
        const containerRect = document.querySelector('.swiper').getBoundingClientRect();
        
        spine.style.opacity = '1';
        spine.style.left = `${slideRect.left - containerRect.left}px`;
    } else {
        // Hide spine on non-cover slides
        spine.style.opacity = '0';
    }
}

// Get story ID from URL parameter
const params = getUrlParams();
const storyId = params.id;

// Main initialization
document.addEventListener('DOMContentLoaded', async () => {
    if (!storyId) {
        document.body.innerHTML = '<div style="padding: 20px; color: red;">Error: No story ID provided. Please go back and select a story.</div>';
        return;
    }
    
    const storyData = await loadStory(storyId);
    if (storyData) {
        formatStorybook(storyData);
        
        // Update window resize and orientation change event listeners
        window.addEventListener('resize', updateSpineVisibility);
        window.addEventListener('orientationchange', () => {
            setTimeout(updateSpineVisibility, 300);
        });
    }
}); 