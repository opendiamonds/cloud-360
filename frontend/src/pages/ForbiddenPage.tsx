import React from 'react';
import { useNavigate } from 'react-router-dom';

export const ForbiddenPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen w-screen flex flex-col items-center justify-center bg-slate-900 text-white font-sans">
      <div className="max-w-md w-full p-8 text-center flex flex-col items-center gap-6">
        <div className="w-20 h-20 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center border border-red-500/20 shadow-lg">
          <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0-8v6m0 5h.01M4.93 19h14.14c1.25 0 2-1.35 1.34-2.45L13.34 4c-.65-1.1-2.03-1.1-2.68 0L3.59 16.55c-.66 1.1.09 2.45 1.34 2.45z" />
          </svg>
        </div>
        
        <div>
          <h1 className="text-5xl font-black text-white tracking-tight">403</h1>
          <h2 className="text-xl font-bold text-slate-300 mt-2">存取被拒 (Access Denied)</h2>
          <p className="text-sm text-slate-400 mt-3 font-medium leading-relaxed">
            抱歉，您的角色權限不足以訪問此資源或管理面板。如果您認為這是一個錯誤，請聯絡您的系統管理員變更角色權限。
          </p>
        </div>

        <div className="flex gap-3 w-full mt-4">
          <button 
            onClick={() => navigate('/workspace')}
            className="flex-1 py-4 bg-slate-800 text-slate-200 text-sm font-bold rounded-2xl hover:bg-slate-700 transition-colors border border-slate-700"
          >
            返回架構工作區
          </button>
        </div>
      </div>
    </div>
  );
};
