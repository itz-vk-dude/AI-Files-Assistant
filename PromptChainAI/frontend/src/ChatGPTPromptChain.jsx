import React, { useState, useRef, useEffect } from 'react';
import { Send, Upload, FileText, Folder, Download, Settings, User, MessageSquare, Link, Database, Zap, RefreshCw, Copy, Check, Mic, MicOff, ThumbsUp, ThumbsDown } from 'lucide-react';

const ChatGPTPromptChain = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'system',
      content: 'Welcome to AI Files Assistant! I can help you create and execute complex File operations using data from your Google Drive. What would you like to work on today?',
      timestamp: new Date().toISOString()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChain, setCurrentChain] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [copied, setCopied] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [recognition, setRecognition] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [driveFiles, setDriveFiles] = useState({});
  const [folderId, setFolderId] = useState('');
  const [showFolderPrompt, setShowFolderPrompt] = useState(false);
  const [connected, setConnected] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [ratings, setRatings] = useState({});
  const [useBestAnswerMode, setUseBestAnswerMode] = useState(true); // ✅ RLHF mode toggle
  const messagesEndRef = useRef(null);

  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-US';
      
      recognitionInstance.onstart = () => {
        setIsListening(true);
      };
      
      recognitionInstance.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0])
          .map(result => result.transcript)
          .join('');
        
        setInputValue(transcript);
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
        setIsListening(false);
      };
      
      recognitionInstance.onend = () => {
        setIsRecording(false);
        setIsListening(false);
      };
      
      setRecognition(recognitionInstance);
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat history on component mount
  useEffect(() => {
    // Chat history will be loaded when user connects to Drive
    setChatHistory([]);
  }, []);

  const handleRateResponse = async (messageId, rating) => {
    try {
      // Update local state immediately
      setRatings(prev => ({ ...prev, [messageId]: rating }));
      
      // Send rating to backend
      await fetch('http://localhost:8000/rate_response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          rating: rating,
          folder_id: folderId
        })
      });
      
      console.log(`Response ${messageId} rated: ${rating}`);
    } catch (error) {
      console.error('Failed to rate response:', error);
      // Revert local state on error
      setRatings(prev => {
        const newRatings = { ...prev };
        delete newRatings[messageId];
        return newRatings;
      });
    }
  };

  const handleLoadFromDrive = async () => {
    if (!folderId) {
      setShowFolderPrompt(true);
      return;
    }

    setIsLoadingFiles(true);
    
    try {
      const res = await fetch(`http://localhost:8000/load_drive?folder_id=${folderId}`);
      const data = await res.json();
      setDriveFiles(data.files || {});
      setConnected(true);
      console.log('✅ Drive files loaded:', data.files);

      // Also load chat history
      const histRes = await fetch(`http://localhost:8000/load_history?folder_id=${folderId}`);
      const histData = await histRes.json();
      if (histData.history && histData.history.length > 0) {
        setMessages(histData.history);
      }

      // Show success message
      const loadMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: `Successfully loaded ${Object.keys(data.files || {}).length} files from Google Drive! Your files are now ready for processing.`,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, loadMessage]);
    } catch (e) {
      console.error('❌ Failed to load drive or history:', e);
      setConnected(false);
      
      // Show error message
      const errorMessage = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: `Failed to load files from Google Drive. Please check your connection and folder ID. Error: ${e.message}`,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    }
    
    setIsLoadingFiles(false);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setIsLoading(true);

    // Show processing chain
    setCurrentChain({
      steps: [
        { name: 'Processing Query', status: 'completed' },
        { name: 'Analyzing Files', status: 'in-progress' },
        { name: 'Generating Response', status: 'pending' }
      ]
    });

    try {
      const endpoint = useBestAnswerMode ? '/ask_best' : '/ask'; // ✅ Toggle endpoint
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage.content,
          folder_id: folderId,
          history: newMessages
        })
      });

      const json = await res.json();

      // Update processing chain
      setCurrentChain({
        steps: [
          { name: 'Processing Query', status: 'completed' },
          { name: 'Analyzing Files', status: 'completed' },
          { name: 'Generating Response', status: 'completed' }
        ]
      });

      const aiResponse = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: json.answer || 'No response received from the server.',
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, aiResponse]);
    } catch (e) {
      console.error('❌ Failed to send message:', e);
      
      const errorResponse = {
        id: crypto.randomUUID(),
        type: 'assistant',
        content: `Sorry, I encountered an error while processing your request: ${e.message}. Please check your connection and try again.`,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, errorResponse]);
    }

    setIsLoading(false);
    setCurrentChain(null);
  };

  const handleChatSelect = (chat) => {
    // Load selected chat history
    console.log('Loading chat:', chat.title);
    // Here you would typically load the chat messages from your backend
  };

  const toggleVoiceInput = () => {
    if (!recognition) {
      alert('Speech recognition is not supported in your browser. Please use Chrome, Safari, or Edge.');
      return;
    }

    if (isRecording) {
      recognition.stop();
      setIsRecording(false);
    } else {
      recognition.start();
      setIsRecording(true);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'csv': return <FileText className="w-4 h-4 text-green-500" />;
      case 'docx': return <FileText className="w-4 h-4 text-blue-500" />;
      case 'xlsx': return <FileText className="w-4 h-4 text-green-600" />;
      case 'pdf': return <FileText className="w-4 h-4 text-red-500" />;
      case 'json': return <FileText className="w-4 h-4 text-purple-500" />;
      default: return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  const getFileExtension = (filename) => {
    return filename.split('.').pop()?.toLowerCase() || '';
  };

  const formatFileSize = (filename) => {
    // Mock file size calculation based on filename
    const length = filename.length;
    if (length < 20) return `${(Math.random() * 2 + 0.5).toFixed(1)} MB`;
    if (length < 30) return `${(Math.random() * 5 + 1).toFixed(1)} MB`;
    return `${(Math.random() * 10 + 2).toFixed(1)} MB`;
  };

  const driveFilesArray = Object.keys(driveFiles).map(filename => ({
    id: filename,
    name: filename,
    type: getFileExtension(filename),
    size: formatFileSize(filename),
    lastModified: 'Recently'
  }));

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 bg-white border-r border-gray-200 overflow-hidden`}>
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-4">
            <Link className="w-6 h-6 text-indigo-600" />
            <h2 className="text-lg font-semibold text-gray-800">AI Files</h2>
          </div>
          
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
            <MessageSquare className="w-4 h-4" />
            <span>Chat History</span>
            <button className="ml-auto p-1 hover:bg-gray-100 rounded">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-4 max-h-96 overflow-y-auto">
          {chatHistory.map(chat => (
            <div
              key={chat.id}
              className="p-3 rounded-lg border mb-2 cursor-pointer transition-all hover:border-gray-300 hover:bg-gray-50"
              onClick={() => handleChatSelect(chat)}
            >
              <div className="flex items-start gap-3">
                <MessageSquare className="w-4 h-4 text-indigo-500 mt-1" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{chat.title}</p>
                  <p className="text-xs text-gray-500 truncate mb-1">{chat.lastMessage}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">{chat.timestamp}</span>
                    <span className="text-xs text-gray-400">{chat.messageCount} messages</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Database className={`w-4 h-4 ${connected ? 'text-green-500' : 'text-gray-400'}`} />
              <span className="text-sm font-medium text-gray-700">Google Drive Files</span>
            </div>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
              {driveFilesArray.length} files
            </span>
          </div>
          
          <button
            onClick={() => setShowFolderPrompt(true)}
            disabled={isLoadingFiles}
            className="w-full mb-3 px-3 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {isLoadingFiles ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Loading...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Load from Drive
              </>
            )}
          </button>
          
          <div className="text-xs text-gray-500 mb-3">
            {connected ? 'Files synced and ready for processing' : 'Connect to Google Drive to load files'}
          </div>
          
          {driveFilesArray.length > 0 ? (
            <div className="max-h-40 overflow-y-auto space-y-2">
              {driveFilesArray.slice(0, 5).map(file => (
                <div key={file.id} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded-lg cursor-pointer">
                  {getFileIcon(file.type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-700 truncate">{file.name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>{file.size}</span>
                      <span>•</span>
                      <span>{file.lastModified}</span>
                    </div>
                  </div>
                </div>
              ))}
              {driveFilesArray.length > 5 && (
                <div className="text-xs text-center text-gray-500 py-1">
                  +{driveFilesArray.length - 5} more files
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-gray-400 text-center py-4">
              {connected ? 'No files found in the specified folder' : 'No files loaded yet'}
            </div>
          )}
        </div>

        {currentChain && (
          <div className="p-4 border-t border-gray-200">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">Processing Status</span>
            </div>
            <div className="space-y-2">
              {currentChain.steps.map((step, index) => (
                <div key={index} className="flex items-center gap-2 text-sm">
                  <div className={`w-2 h-2 rounded-full ${
                    step.status === 'completed' ? 'bg-green-500' :
                    step.status === 'in-progress' ? 'bg-yellow-500' :
                    'bg-gray-300'
                  }`} />
                  <span className={`${
                    step.status === 'completed' ? 'text-green-700' :
                    step.status === 'in-progress' ? 'text-yellow-700' :
                    'text-gray-500'
                  }`}>{step.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <Folder className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-2">
                <Link className="w-6 h-6 text-indigo-600" />
                <h1 className="text-xl font-semibold text-gray-800">AI Files Assistant</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-sm text-gray-500 px-3 py-1 rounded-full border border-gray-300">
                Mode: <span className={useBestAnswerMode ? 'text-green-600 font-medium' : 'text-yellow-600 font-medium'}>
                  {useBestAnswerMode ? '🔥 Best Answer (RLHF)' : '⚙️ Normal'}</span>
              </div>
              <button
                onClick={() => setUseBestAnswerMode(!useBestAnswerMode)}
                className="p-2 bg-gray-100 hover:bg-gray-200 text-sm rounded-lg"
                title="Toggle answer mode"
              >
                <Zap className="w-4 h-4" />
              </button>

              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <Settings className="w-5 h-5" />
              </button>
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}>
                <User className="w-4 h-4" />
                <span className="text-sm">
                  {connected ? 'Connected to Google Drive' : 'Not Connected'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-4xl rounded-2xl px-4 py-3 ${
                message.type === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
              }`}>
                <div className="flex items-start gap-3">
                  {message.type === 'assistant' && (
                    <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mt-1">
                      <Link className="w-4 h-4 text-indigo-600" />
                    </div>
                  )}
                  <div className="flex-1">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
                    {message.type === 'assistant' && (
                      <div className="flex items-center gap-2 mt-3">
                        <button
                          onClick={() => copyToClipboard(message.content)}
                          className="p-1 hover:bg-gray-100 rounded transition-colors"
                        >
                          {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-500" />}
                        </button>
                        
                        {/* Rating buttons */}
                        <div className="flex items-center gap-1 ml-2">
                          <button
                            onClick={() => handleRateResponse(message.id, 'positive')}
                            className={`p-1 rounded transition-colors ${
                              ratings[message.id] === 'positive' 
                                ? 'bg-green-100 text-green-600' 
                                : 'hover:bg-gray-100 text-gray-500'
                            }`}
                            title="Good response"
                          >
                            <ThumbsUp className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleRateResponse(message.id, 'negative')}
                            className={`p-1 rounded transition-colors ${
                              ratings[message.id] === 'negative' 
                                ? 'bg-red-100 text-red-600' 
                                : 'hover:bg-gray-100 text-gray-500'
                            }`}
                            title="Poor response"
                          >
                            <ThumbsDown className="w-4 h-4" />
                          </button>
                        </div>
                        
                        <span className="text-xs text-gray-500 ml-auto">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                    <Link className="w-4 h-4 text-indigo-600" />
                  </div>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask me about your Google Drive files or start a new conversation..."
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                disabled={isLoading}
              />
              {isListening && (
                <div className="absolute right-12 top-3 flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-red-500">Listening...</span>
                </div>
              )}
            </div>
            <button
              onClick={toggleVoiceInput}
              className={`p-3 rounded-xl transition-colors ${
                isRecording 
                  ? 'bg-red-500 text-white hover:bg-red-600' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              disabled={isLoading}
              title={isRecording ? 'Stop recording' : 'Start voice input'}
            >
              {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !inputValue.trim()}
              className="bg-indigo-600 text-white p-3 rounded-xl hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Folder ID Prompt Modal */}
      {showFolderPrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-[500px] shadow-2xl max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Connect to Google Drive</h2>
            
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-700 mb-3">Setup Instructions:</h3>
              <div className="space-y-3 text-sm text-gray-600">
                <p>1. Go to Google Drive.</p>
                <p>2. Find the folder (or file) you want your app to access.</p>
                <p>3. <strong>Right-click</strong> on the folder → Click <strong>"Share"</strong>.</p>
                <p>4. In the "Share with people and groups" box, <strong>paste</strong> your service account email:</p>
                
                <div className="bg-gray-50 p-3 rounded-lg border">
                  <code className="text-sm text-gray-800 break-all">
                    promptchain-sa@driveragbot.iam.gserviceaccount.com
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText('promptchain-sa@driveragbot.iam.gserviceaccount.com');
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="ml-2 p-1 hover:bg-gray-200 rounded transition-colors"
                    title="Copy service account email"
                  >
                    {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-500" />}
                  </button>
                </div>
                
                <p>5. Set permission as <strong>Viewer</strong> or <strong>Editor</strong> (Viewer is enough for reading).</p>
                <p>6. Click <strong>"Send"</strong> or <strong>"Share"</strong>.</p>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Enter your Google Drive folder ID:
              </label>
              <input
                type="text"
                value={folderId}
                onChange={(e) => setFolderId(e.target.value)}
                placeholder="Enter folder ID..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={() => setShowFolderPrompt(false)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowFolderPrompt(false);
                  handleLoadFromDrive();
                }}
                disabled={!folderId.trim()}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatGPTPromptChain;