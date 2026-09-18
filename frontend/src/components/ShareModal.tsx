import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';

interface User {
  id: number;
  username: string;
  role: string;
}

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  diagramId: number | null;
  token: string;
}

export const ShareModal = ({ isOpen, onClose, diagramId, token }: ShareModalProps) => {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && diagramId && token) {
      // 1. 取得所有可分享的使用者
      fetch(apiUrl('/api/collab/users'), {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(err => console.error(err));

      // 2. 取得此圖表已經分享的使用者
      fetch(apiUrl(`/api/collab/diagrams/${diagramId}`), {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      .then(res => res.json())
      .then(data => {
        if (data.shared_user_ids) {
          setSelectedUserIds(data.shared_user_ids);
        }
      })
      .catch(err => console.error(err));
    }
  }, [isOpen, diagramId, token]);

  if (!isOpen) return null;

  const toggleUser = (id: number) => {
    setSelectedUserIds(prev => 
      prev.includes(id) ? prev.filter(uId => uId !== id) : [...prev, id]
    );
  };

  const handleShare = async () => {
    if (!diagramId) return;
    setIsLoading(true);
    try {
      const res = await fetch(apiUrl(`/api/collab/diagrams/${diagramId}/share`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ user_ids: selectedUserIds })
      });
      if (res.ok) {
        alert('分享設定已更新！');
        onClose();
      } else {
        const data = await res.json();
        alert(data.detail || '分享失敗，可能權限不足。');
      }
    } catch {
      alert('分享失敗');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center animate-[fadeIn_0.2s_ease-out]">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden animate-[slideInUp_0.3s_ease-out]">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <svg className="w-5 h-5 text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            與團隊分享
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-1.5 rounded-lg transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {users.length === 0 ? (
            <p className="text-gray-500 text-center py-8">載入中或無其他使用者...</p>
          ) : (
            <div className="space-y-2">
              {users.map(user => (
                <label key={user.id} className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 hover:bg-brand-50 hover:border-brand-100 cursor-pointer transition-colors">
                  <div className="relative flex items-center">
                    <input 
                      type="checkbox" 
                      className="w-5 h-5 border-gray-300 rounded text-brand-600 focus:ring-brand-500 transition-all"
                      checked={selectedUserIds.includes(user.id)}
                      onChange={() => toggleUser(user.id)}
                    />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-800">{user.username}</span>
                    <span className="text-xs font-medium text-gray-500">{user.role}</span>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-100 bg-gray-50/50 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-5 py-2.5 text-sm font-bold text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-all"
          >
            取消
          </button>
          <button 
            onClick={handleShare}
            disabled={isLoading}
            className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-bold rounded-xl shadow-md hover:shadow-lg hover:shadow-brand-500/30 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {isLoading ? '儲存中...' : '確認分享'}
          </button>
        </div>
      </div>
    </div>
  );
};
