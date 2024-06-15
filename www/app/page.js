// pages/index.js
'use client';

import { useState } from 'react';
import axios from 'axios';
import { parsePhoneNumberFromString } from 'libphonenumber-js';

export default function Home() {
    const [urls, setUrls] = useState([]);
    const [loading, setLoading] = useState(false);
    const [phoneNumber, setPhoneNumber] = useState('');
    const [currentUrl, setCurrentUrl] = useState('');

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (currentUrl.trim()) {
                setUrls([...urls, currentUrl.trim()]);
                setCurrentUrl('');
            }
        }
    };

    const handleRemoveUrl = (index) => {
        const newUrls = urls.filter((_, i) => i !== index);
        setUrls(newUrls);
    };

    const handleSubmit = async () => {
        setLoading(true);
        try {
            const response = await axios.post('http://localhost:5000/create_agent', {
                urls,
            });
            const rawPhoneNumber = response.data.phone_number;
            const formattedPhoneNumber = formatPhoneNumber(rawPhoneNumber);
            setPhoneNumber(formattedPhoneNumber);
        } catch (error) {
            console.error(error);
            alert('An error occurred while generating the phone number.');
        } finally {
            setLoading(false);
        }
    };

    const formatPhoneNumber = (phoneNumber) => {
        const parsedNumber = parsePhoneNumberFromString(phoneNumber, 'US');
        return parsedNumber ? parsedNumber.formatInternational() : phoneNumber;
    };

    return (
        <div className="min-h-screen flex flex-col justify-center items-center bg-gray-50">
            <div className="max-w-[400px] w-full text-center">
                <h1 className="text-3xl mb-2">Flyflow Support Generator</h1>
                <p className="mb-6">
                    Enter URLs for supporting documentation to generate a support phone number
                </p>
                <textarea
                    value={currentUrl}
                    onChange={(e) => setCurrentUrl(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter one URL and press Enter"
                    className="border p-4 w-full h-20 mb-4"
                ></textarea>
                <div className="flex flex-wrap gap-2 mb-4">
                    {urls.map((url, index) => (
                        <div key={index} className="flex items-center bg-gray-200 rounded-full px-3 py-1">
                            <span className="mr-2">{url}</span>
                            <button onClick={() => handleRemoveUrl(index)} className="text-red-500">
                                x
                            </button>
                        </div>
                    ))}
                </div>
                <button
                    onClick={handleSubmit}
                    className="bg-[#095C37] text-white px-6 py-3 rounded-lg text-lg w-full"
                    disabled={loading}
                >
                    {loading ? 'Loading...' : 'Generate Phone Number'}
                </button>
                {phoneNumber && (
                    <div className="text-center mt-10">
                        <p className="text-xl">Support Phone Number</p>
                        <p className="text-4xl font-bold mt-2">{phoneNumber}</p>
                    </div>
                )}
            </div>
        </div>
    );
}
