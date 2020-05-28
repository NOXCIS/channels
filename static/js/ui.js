"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
/**
 * Get server response from add channel request to server.
 * @param channelName  name of the channel to be added.
 * @return Promise with JSON of the response.
 */
function getResponseAddChannel(channelName) {
    return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/add-channel');
        xhr.responseType = 'json';
        xhr.onload = () => {
            resolve(xhr.response);
        };
        const form = new FormData();
        form.append('channelName', channelName);
        xhr.send(form);
    });
}
/**
 * Close the modal after adding a channel.
 */
function closeModal() {
    const closeButton = document.querySelector('#add-channel-close-button');
    closeButton.click();
}
/**
 * Show an alert after sending an invalid channel name.
 * @param error  error message.
 */
function invalidChannelName(error) {
    alert(`Invalid channel name, error message: ${error}.`);
}
/**
 * Show an alert after successfully adding a channel.
 */
function addChannelMessage() {
    alert('The channel was successfully added!');
}
/**
 * Manage the add channel modal. If input field has a valid channel name, create a channel.
 * Otherwise, show a corresponding error.
 */
function addChannelModal() {
    const input = document.querySelector('#add-channel-input');
    const addButton = document.querySelector('#add-channel-add-button');
    addButton.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
        const channelName = input.value;
        const responseAddChannel = yield getResponseAddChannel(channelName);
        if (responseAddChannel.success) {
            addChannelMessage();
            closeModal();
        }
        else {
            invalidChannelName(responseAddChannel.errorMessage);
        }
    }));
}
document.addEventListener('DOMContentLoaded', () => {
    addChannelModal();
});